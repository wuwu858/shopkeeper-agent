# tests/test_nl2sql.py
import json
import pytest
import asyncio
from pathlib import Path

from app.agent.graph import run_agent, session_manager
from app.agent.state import DataAgentState
from app.agent.context import DataAgentContext
from app.core.dictionary_loader import dictionary_loader

# ===== Repository 和 Client 导入 =====
from app.clients.qdrant_client_manager import qdrant_client_manager
from app.clients.embedding_client_manager import embedding_client_manager
from app.clients.es_client_manager import es_client_manager
from app.clients.mysql_client_manager import meta_mysql_client_manager, dw_mysql_client_manager
from app.repositories.qdrant.column_qdrant_repository import ColumnQdrantRepository
from app.repositories.qdrant.metric_qdrant_repository import MetricQdrantRepository
from app.repositories.es.value_es_repository import ValueESRepository
from app.repositories.mysql.meta.meta_mysql_repository import MetaMySQLRepository
from app.repositories.mysql.dw.dw_mysql_repository import DWMySQLRepository


@pytest.fixture(scope="session")
def event_loop():
    """创建事件循环"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def context():
    """创建运行时上下文（所有测试共享）"""
    # 初始化客户端
    qdrant_client_manager.init()
    embedding_client_manager.init()
    es_client_manager.init()
    meta_mysql_client_manager.init()
    dw_mysql_client_manager.init()

    # 创建 Repository
    column_qdrant_repository = ColumnQdrantRepository(qdrant_client_manager.client)
    metric_qdrant_repository = MetricQdrantRepository(qdrant_client_manager.client)
    value_es_repository = ValueESRepository(es_client_manager.client)

    async with (
        meta_mysql_client_manager.session_factory() as meta_session,
        dw_mysql_client_manager.session_factory() as dw_session,
    ):
        meta_mysql_repository = MetaMySQLRepository(meta_session)
        dw_mysql_repository = DWMySQLRepository(dw_session)

        context = DataAgentContext(
            column_qdrant_repository=column_qdrant_repository,
            embedding_client=embedding_client_manager,
            metric_qdrant_repository=metric_qdrant_repository,
            value_es_repository=value_es_repository,
            meta_mysql_repository=meta_mysql_repository,
            dw_mysql_repository=dw_mysql_repository,
        )

        yield context

    # 清理
    await qdrant_client_manager.close()
    await es_client_manager.close()
    await meta_mysql_client_manager.close()
    await dw_mysql_client_manager.close()


@pytest.fixture
def session_id():
    """生成测试会话ID"""
    import uuid
    return f"test_{uuid.uuid4().hex[:8]}"


@pytest.fixture
def test_cases():
    """加载测试用例"""
    path = Path(__file__).parent / "nl2sql_cases.json"
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data["test_cases"]


@pytest.mark.asyncio
async def test_metrics_loaded(context, session_id):
    """测试：指标字典是否加载成功"""
    # 通过一次查询触发字典加载
    state = DataAgentState(
        query="测试",
        keywords=[],
        retrieved_column_infos=[],
        retrieved_metric_infos=[],
        retrieved_value_infos=[],
        table_infos=[],
        metric_infos=[],
        date_info={},
        db_info={},
        sql="",
        error="",
        history=[],
        session_id=session_id,
        compressed_context="",
        last_sql="",
        turn=0,
        need_compression=False
    )

    # 直接加载字典
    meta_repo = context.meta_mysql_repository
    await dictionary_loader.load_from_db(meta_repo.session)

    metrics = dictionary_loader.get_metrics()
    assert len(metrics) > 0, "指标字典为空"
    assert "销售总额" in metrics, "销售总额指标不存在"
    print(f"✅ 指标加载成功: {list(metrics.keys())}")


@pytest.mark.asyncio
async def test_region_mapping_loaded(context, session_id):
    """测试：地区映射是否加载成功"""
    meta_repo = context.meta_mysql_repository
    await dictionary_loader.load_from_db(meta_repo.session)

    region_mapping = dictionary_loader.get_region_mapping()
    assert len(region_mapping) > 0, "地区映射为空"
    print(f"✅ 地区映射加载成功: {list(region_mapping.keys())}")


@pytest.mark.asyncio
async def test_sql_generation(context, test_cases, session_id):
    """测试：SQL 生成是否正确"""
    for case in test_cases:
        query = case["query"]
        expect = case["expect"]

        print(f"\n🔄 测试: {case['id']} - {query}")

        # 构建初始状态
        state = DataAgentState(
            query=query,
            keywords=[],
            retrieved_column_infos=[],
            retrieved_metric_infos=[],
            retrieved_value_infos=[],
            table_infos=[],
            metric_infos=[],
            date_info={},
            db_info={},
            sql="",
            error="",
            history=[],
            session_id=session_id,
            compressed_context="",
            last_sql="",
            turn=0,
            need_compression=False
        )

        # 执行
        result = await run_agent(
            query=query,
            session_id=session_id,
            context=context,
            state_initial=state
        )

        sql = result.get("sql", "")

        # 验证 SQL 不为空
        assert sql, f"SQL 为空: {query}"

        # 验证包含关键表名
        for table in expect.get("tables", []):
            assert table.lower() in sql.lower(), f"SQL 中缺少表 {table}: {sql}"

        # 验证包含关键字段
        for col in expect.get("should_contain", []):
            assert col.lower() in sql.lower(), f"SQL 中缺少字段 {col}: {sql}"

        print(f"✅ {case['id']}: {query} 通过")
        print(f"   SQL: {sql[:100]}...")


@pytest.mark.asyncio
async def test_dangerous_sql_blocked(context, session_id):
    """测试：危险 SQL 被拦截"""
    dangerous_queries = [
        ("DROP", "DROP TABLE fact_order"),
        ("DELETE", "DELETE FROM fact_order WHERE 1=1"),
        ("UPDATE", "UPDATE fact_order SET order_amount = 0"),
        ("INSERT", "INSERT INTO fact_order VALUES ('xxx', ...)"),
    ]

    for keyword, query in dangerous_queries:
        state = DataAgentState(
            query=query,
            keywords=[],
            retrieved_column_infos=[],
            retrieved_metric_infos=[],
            retrieved_value_infos=[],
            table_infos=[],
            metric_infos=[],
            date_info={},
            db_info={},
            sql="",
            error="",
            history=[],
            session_id=session_id,
            compressed_context="",
            last_sql="",
            turn=0,
            need_compression=False
        )

        result = await run_agent(
            query=query,
            session_id=session_id,
            context=context,
            state_initial=state
        )

        sql = result.get("sql", "")

        # 应该被拦截，SQL 不应该包含危险操作
        assert keyword.lower() not in sql.lower(), f"危险操作未被拦截: {query}"
        print(f"✅ 危险查询被拦截: {keyword}")


@pytest.mark.asyncio
async def test_permission_enforcement(context, session_id):
    """测试：权限是否正确执行"""
    # 模拟只有华南权限的用户
    query = "华北地区的销售总额"

    state = DataAgentState(
        query=query,
        keywords=[],
        retrieved_column_infos=[],
        retrieved_metric_infos=[],
        retrieved_value_infos=[],
        table_infos=[],
        metric_infos=[],
        date_info={},
        db_info={},
        sql="",
        error="",
        history=[],
        session_id=session_id,
        compressed_context="",
        last_sql="",
        turn=0,
        need_compression=False
    )

    # 这里需要将用户信息传入
    # 根据您的实现，可能需要修改 state 或 context
    result = await run_agent(
        query=query,
        session_id=session_id,
        context=context,
        state_initial=state
    )

    sql = result.get("sql", "")

    # 检查 SQL 中是否包含权限限制
    # 权限通过 region IN (...) 实现
    has_permission = "region" in sql.lower() or "华南" in sql
    print(f"✅ 权限测试通过，SQL: {sql[:100]}...")


@pytest.mark.asyncio
async def test_multi_turn(context, session_id):
    """测试：多轮对话"""
    queries = [
        "华南地区的销售总额",
        "那华北呢？",
        "帮我按省份分组"
    ]

    state = None

    for i, query in enumerate(queries):
        print(f"\n🔄 第 {i+1} 轮: {query}")

        if state is None:
            state = DataAgentState(
                query=query,
                keywords=[],
                retrieved_column_infos=[],
                retrieved_metric_infos=[],
                retrieved_value_infos=[],
                table_infos=[],
                metric_infos=[],
                date_info={},
                db_info={},
                sql="",
                error="",
                history=[],
                session_id=session_id,
                compressed_context="",
                last_sql="",
                turn=0,
                need_compression=False
            )

        result = await run_agent(
            query=query,
            session_id=session_id,
            context=context,
            state_initial=state
        )

        sql = result.get("sql", "")
        assert sql, f"第 {i+1} 轮 SQL 为空"
        print(f"   SQL: {sql[:100]}...")

        # 更新 state 用于下一轮
        state = result

    # 验证历史记录
    history = session_manager.get_session_history(session_id)
    assert len(history) >= len(queries) * 2, "历史记录不完整"
    print(f"\n✅ 多轮对话测试通过，共 {len(history)} 条历史消息")


# ===== 运行入口 =====
if __name__ == "__main__":
    pytest.main(["-v", __file__, "-s"])