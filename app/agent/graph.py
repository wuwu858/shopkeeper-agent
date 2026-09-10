import asyncio
from langgraph.graph import StateGraph, END
from langgraph.runtime import Runtime

from app.agent.context import DataAgentContext
from app.agent.nodes.compress_context import compress_context  # ✅ 新增导入
from app.agent.nodes.extract_keywords import extract_keywords
from app.agent.nodes.recall_column import recall_column
from app.agent.nodes.recall_metric import recall_metric
from app.agent.nodes.recall_value import recall_value
from app.agent.nodes.merge_retrieved_info import merge_retrieved_info
from app.agent.nodes.filter_table import filter_table
from app.agent.nodes.filter_metric import filter_metric
from app.agent.nodes.add_extra_context import add_extra_context
from app.agent.nodes.generate_sql import generate_sql
from app.agent.nodes.validate_sql import validate_sql
from app.agent.nodes.correct_sql import correct_sql
from app.agent.nodes.run_sql import run_sql
from app.agent.state import DataAgentState
from app.clients.qdrant_client_manager import qdrant_client_manager
from app.clients.embedding_client_manager import embedding_client_manager
from app.clients.es_client_manager import es_client_manager
from app.clients.mysql_client_manager import meta_mysql_client_manager, dw_mysql_client_manager
from app.repositories.qdrant.column_qdrant_repository import ColumnQdrantRepository
from app.repositories.qdrant.metric_qdrant_repository import MetricQdrantRepository
from app.repositories.es.value_es_repository import ValueESRepository
from app.repositories.mysql.meta.meta_mysql_repository import MetaMySQLRepository
from app.repositories.mysql.dw.dw_mysql_repository import DWMySQLRepository


def build_graph():
    """
    构建问数智能体的 LangGraph 工作流

    工作流（含多轮对话支持）：
    1. compress_context     - 压缩对话历史（新增）
    2. extract_keywords     - 抽取关键词
    3. recall_column/metric/value - 三路并行召回
    4. merge_retrieved_info - 合并召回结果
    5. filter_table/metric  - 并行过滤
    6. add_extra_context    - 添加上下文
    7. generate_sql         - 生成 SQL（使用上下文）
    8. validate_sql         - 校验 SQL
    9. correct_sql          - 校正 SQL（如需要）
    10. run_sql             - 执行 SQL（保存历史）
    """

    graph_builder = StateGraph(DataAgentState)

    # ✅ 添加节点（新增 compress_context）
    graph_builder.add_node("compress_context", compress_context)
    graph_builder.add_node("extract_keywords", extract_keywords)
    graph_builder.add_node("recall_column", recall_column)
    graph_builder.add_node("recall_metric", recall_metric)
    graph_builder.add_node("recall_value", recall_value)
    graph_builder.add_node("merge_retrieved_info", merge_retrieved_info)
    graph_builder.add_node("filter_table", filter_table)
    graph_builder.add_node("filter_metric", filter_metric)
    graph_builder.add_node("add_extra_context", add_extra_context)
    graph_builder.add_node("generate_sql", generate_sql)
    graph_builder.add_node("validate_sql", validate_sql)
    graph_builder.add_node("correct_sql", correct_sql)
    graph_builder.add_node("run_sql", run_sql)

    # ✅ 修改入口：先压缩上下文，再抽取关键词
    graph_builder.set_entry_point("compress_context")

    # ✅ 从压缩上下文到关键词抽取
    graph_builder.add_edge("compress_context", "extract_keywords")

    # 关键词抽取后并行三路召回
    graph_builder.add_edge("extract_keywords", "recall_column")
    graph_builder.add_edge("extract_keywords", "recall_metric")
    graph_builder.add_edge("extract_keywords", "recall_value")

    # 三路召回汇入合并节点
    graph_builder.add_edge("recall_column", "merge_retrieved_info")
    graph_builder.add_edge("recall_metric", "merge_retrieved_info")
    graph_builder.add_edge("recall_value", "merge_retrieved_info")

    # 合并后分流到过滤
    graph_builder.add_edge("merge_retrieved_info", "filter_table")
    graph_builder.add_edge("merge_retrieved_info", "filter_metric")

    # 过滤后汇入添加上下文
    graph_builder.add_edge("filter_table", "add_extra_context")
    graph_builder.add_edge("filter_metric", "add_extra_context")

    # 生成 SQL -> 校验 SQL
    graph_builder.add_edge("add_extra_context", "generate_sql")
    graph_builder.add_edge("generate_sql", "validate_sql")

    # 条件分支：校验通过则执行，失败则校正
    graph_builder.add_conditional_edges(
        source="validate_sql",
        path=lambda state: "run_sql" if not state.get("error") else "correct_sql",
        path_map={"run_sql": "run_sql", "correct_sql": "correct_sql"},
    )

    # 校正后执行
    graph_builder.add_edge("correct_sql", "run_sql")
    graph_builder.add_edge("run_sql", END)

    return graph_builder.compile()


# 创建全局图实例
graph = build_graph()


# ✅ 新增：多轮对话会话管理
class SessionManager:
    """对话会话管理器"""

    def __init__(self):
        self._sessions = {}

    def get_or_create_session(self, session_id: str) -> dict:
        """获取或创建会话"""
        if session_id not in self._sessions:
            self._sessions[session_id] = {
                "history": [],
                "turn": 0,
                "last_sql": "",
                "created_at": asyncio.get_event_loop().time()
            }
        return self._sessions[session_id]

    def update_session(self, session_id: str, state: dict):
        """更新会话状态"""
        if session_id in self._sessions:
            self._sessions[session_id].update({
                "history": state.get("history", []),
                "turn": state.get("turn", 0),
                "last_sql": state.get("last_sql", ""),
                "updated_at": asyncio.get_event_loop().time()
            })

    def clear_session(self, session_id: str):
        """清除会话"""
        if session_id in self._sessions:
            del self._sessions[session_id]

    def get_session_history(self, session_id: str) -> list:
        """获取会话历史"""
        if session_id in self._sessions:
            return self._sessions[session_id].get("history", [])
        return []


# 全局会话管理器实例
session_manager = SessionManager()


# ✅ 新增：流式执行函数（带会话管理）
async def run_agent_stream(
        query: str,
        session_id: str,
        context: DataAgentContext,
        state_initial: DataAgentState = None
):
    """
    流式执行 Agent（支持多轮对话）

    Args:
        query: 用户问题
        session_id: 会话 ID
        context: 运行时上下文
        state_initial: 初始状态（可选）

    Yields:
        流式输出 chunk
    """
    # 获取或创建会话
    session = session_manager.get_or_create_session(session_id)

    # 构建初始状态
    if state_initial is None:
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
            # ✅ 多轮对话字段
            history=session.get("history", []),
            session_id=session_id,
            compressed_context="",
            last_sql=session.get("last_sql", ""),
            turn=session.get("turn", 0),
            need_compression=False
        )
    else:
        # 使用传入的状态，但确保历史来自会话
        state = state_initial
        state["query"] = query
        state["session_id"] = session_id
        state["history"] = session.get("history", [])
        state["last_sql"] = session.get("last_sql", "")
        state["turn"] = session.get("turn", 0)

    # 流式执行
    async for chunk in graph.astream(
            input=state,
            context=context,
            stream_mode="custom"
    ):
        yield chunk

    # ✅ 更新会话状态（在流程结束后）
    # 注意：实际更新应该在 run_sql 节点完成后进行
    # 这里只是示例，实际更新由 run_sql 节点完成


# ✅ 新增：非流式执行函数
async def run_agent(
        query: str,
        session_id: str,
        context: DataAgentContext,
        state_initial: DataAgentState = None
) -> dict:
    """非流式执行 Agent（支持多轮对话）"""

    # 获取或创建会话
    session = session_manager.get_or_create_session(session_id)

    # 构建初始状态
    if state_initial is None:
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
    else:
        # ✅ 直接使用传入的状态，只更新 query
        state = state_initial
        state["query"] = query
        state["session_id"] = session_id
        # history, last_sql, turn 已经在 state_initial 中，不需要覆盖

    # 执行
    result = await graph.ainvoke(
        input=state,
        context=context
    )

    # ✅ 更新会话（保存历史）
    session_manager.update_session(session_id, result)

    return result


if __name__ == "__main__":

    async def test():
        # 1. 初始化所有客户端
        qdrant_client_manager.init()
        embedding_client_manager.init()
        es_client_manager.init()
        meta_mysql_client_manager.init()
        dw_mysql_client_manager.init()

        # 2. 创建 Repository 实例
        column_qdrant_repository = ColumnQdrantRepository(qdrant_client_manager.client)
        metric_qdrant_repository = MetricQdrantRepository(qdrant_client_manager.client)
        value_es_repository = ValueESRepository(es_client_manager.client)

        # 3. 使用数据库会话创建 Repository
        async with (
            meta_mysql_client_manager.session_factory() as meta_session,
            dw_mysql_client_manager.session_factory() as dw_session,
        ):
            meta_mysql_repository = MetaMySQLRepository(meta_session)
            dw_mysql_repository = DWMySQLRepository(dw_session)

            # 4. 准备 state 和 context
            state = DataAgentState(
                query="统计华北地区的销售总额",
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
                # ✅ 多轮对话初始字段
                history=[],
                session_id="test_session_001",
                compressed_context="",
                last_sql="",
                turn=0,
                need_compression=False
            )

            context = DataAgentContext(
                column_qdrant_repository=column_qdrant_repository,
                embedding_client=embedding_client_manager,
                metric_qdrant_repository=metric_qdrant_repository,
                value_es_repository=value_es_repository,
                meta_mysql_repository=meta_mysql_repository,
                dw_mysql_repository=dw_mysql_repository,
            )

            print("=" * 60)
            print("🚀 测试多轮对话")
            print("=" * 60)

            # 5. 第一轮对话
            print("\n📝 第一轮: 统计华北地区的销售总额")
            print("-" * 40)

            final_state = await run_agent(
                query="统计华南地区的销售总额",
                session_id="test_session_001",
                context=context,
                state_initial=state
            )

            print(f"\n✅ SQL: {final_state.get('sql', '')}")
            print(f"📊 轮次: {final_state.get('turn', 0)}")
            print(f"📝 历史消息数: {len(final_state.get('history', []))}")

            # 6. 第二轮对话（追问）
            print("\n📝 第二轮: 那华北呢？")
            print("-" * 40)

            final_state2 = await run_agent(
                query="那华北呢？",
                session_id="test_session_001",
                context=context,
                state_initial=final_state  # 继承上一轮状态
            )

            print(f"\n✅ SQL: {final_state2.get('sql', '')}")
            print(f"📊 轮次: {final_state2.get('turn', 0)}")
            print(f"📝 历史消息数: {len(final_state2.get('history', []))}")

            # 7. 第三轮对话（排序）
            print("\n📝 第三轮: 帮我按省份排序")
            print("-" * 40)

            final_state3 = await run_agent(
                query="帮我按省份排序",
                session_id="test_session_001",
                context=context,
                state_initial=final_state2
            )

            print(f"\n✅ SQL: {final_state3.get('sql', '')}")
            print(f"📊 轮次: {final_state3.get('turn', 0)}")
            print(f"📝 历史消息数: {len(final_state3.get('history', []))}")

            # 8. 打印完整历史
            print("\n" + "=" * 60)
            print("📋 完整对话历史")
            print("=" * 60)
            for i, msg in enumerate(final_state3.get('history', [])):
                role = "👤用户" if msg.get("role") == "user" else "🤖系统"
                content = msg.get("content", "")[:80]
                sql = msg.get("sql", "")
                print(f"\n[{i + 1}] {role}")
                print(f"  内容: {content}")
                if sql:
                    print(f"  SQL: {sql[:80]}...")

        # 9. 关闭所有客户端连接
        await qdrant_client_manager.close()
        await es_client_manager.close()
        await meta_mysql_client_manager.close()
        await dw_mysql_client_manager.close()


    asyncio.run(test())