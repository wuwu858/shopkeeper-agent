# eval/run_eval.py

import json
import asyncio
import time
from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from pathlib import Path
import sys

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.query_service import QueryService


@dataclass
class EvalResult:
    """单条评测结果"""
    question_id: str
    question: str
    expected_sql: str
    actual_sql: str
    sql_match: bool
    expected_result: Any
    actual_result: Any
    result_match: bool
    steps: List[str]
    total_time: float
    success: bool
    error: str


class EvalRunner:
    """评测执行器"""

    def __init__(self):
        self.service = None

    async def setup(self):
        """初始化评测环境"""
        print("🚀 初始化评测环境...")
        try:
            self.service = await self._get_query_service()
            if self.service:
                print("✅ QueryService 初始化成功")
                # ✅ 调试：检查 embedding_client 类型
                print(f"🔍 embedding_client 类型: {type(self.service.embedding_client)}")
                print(f"🔍 是否有 aembed_query: {hasattr(self.service.embedding_client, 'aembed_query')}")
            else:
                print("❌ QueryService 为 None")
        except Exception as e:
            print(f"❌ 初始化失败: {e}")
            import traceback
            traceback.print_exc()
            self.service = None

    async def _get_query_service(self):
        """获取 QueryService 实例"""
        from app.clients.embedding_client_manager import embedding_client_manager
        from app.clients.qdrant_client_manager import qdrant_client_manager
        from app.clients.es_client_manager import es_client_manager
        from app.clients.mysql_client_manager import (
            dw_mysql_client_manager,
            meta_mysql_client_manager,
        )
        from app.repositories.es.value_es_repository import ValueESRepository
        from app.repositories.mysql.dw.dw_mysql_repository import DWMySQLRepository
        from app.repositories.mysql.meta.meta_mysql_repository import MetaMySQLRepository
        from app.repositories.qdrant.column_qdrant_repository import ColumnQdrantRepository
        from app.repositories.qdrant.metric_qdrant_repository import MetricQdrantRepository

        # 确保客户端已初始化
        print("  📦 初始化客户端...")
        meta_mysql_client_manager.init()
        dw_mysql_client_manager.init()
        qdrant_client_manager.init()
        embedding_client_manager.init()
        es_client_manager.init()

        async with (
            meta_mysql_client_manager.session_factory() as meta_session,
            dw_mysql_client_manager.session_factory() as dw_session,
        ):
            meta_repo = MetaMySQLRepository(meta_session)
            dw_repo = DWMySQLRepository(dw_session)

            column_qdrant_repo = ColumnQdrantRepository(qdrant_client_manager.client)
            metric_qdrant_repo = MetricQdrantRepository(qdrant_client_manager.client)
            value_es_repo = ValueESRepository(es_client_manager.client)

            # ✅ 调试：打印 embedding_client_manager 的类型
            print(f"  🔍 embedding_client_manager 类型: {type(embedding_client_manager)}")
            print(f"  🔍 embedding_client_manager.client 类型: {type(embedding_client_manager.client)}")
            print(f"  🔍 embedding_client_manager 是否有 aembed_query: {hasattr(embedding_client_manager, 'aembed_query')}")

            query_service = QueryService(
                meta_mysql_repository=meta_repo,
                embedding_client=embedding_client_manager,
                dw_mysql_repository=dw_repo,
                column_qdrant_repository=column_qdrant_repo,
                metric_qdrant_repository=metric_qdrant_repo,
                value_es_repository=value_es_repo,
            )

            # ✅ 调试：检查 QueryService 内部的 embedding_client
            print(f"  🔍 QueryService.embedding_client 类型: {type(query_service.embedding_client)}")
            print(f"  🔍 QueryService.embedding_client 是否有 aembed_query: {hasattr(query_service.embedding_client, 'aembed_query')}")

            return query_service

    async def run_single(self, question: Dict) -> EvalResult:
        """执行单条评测"""
        start_time = time.time()
        steps = []
        actual_sql = None
        actual_result = None
        error = None

        if not self.service:
            return EvalResult(
                question_id=question["id"],
                question=question["question"],
                expected_sql=question.get("expected_sql", ""),
                actual_sql="",
                sql_match=False,
                expected_result=question.get("expected_result"),
                actual_result=None,
                result_match=False,
                steps=[],
                total_time=0,
                success=False,
                error="QueryService 未初始化"
            )

        try:
            # 执行查询
            async for chunk in self.service.query(question["question"]):
                if isinstance(chunk, dict):
                    if chunk.get("type") == "progress":
                        steps.append(f"{chunk.get('step')}: {chunk.get('status')}")
                    elif chunk.get("type") == "result":
                        actual_result = chunk.get("data")
                    elif chunk.get("type") == "error":
                        error = chunk.get("message")

        except Exception as e:
            error = str(e)

        total_time = time.time() - start_time
        success = error is None and actual_result is not None

        # 对比 SQL
        sql_match = self._compare_sql(question.get("expected_sql", ""), actual_sql or "")

        # 对比结果
        result_match = self._compare_results(
            question.get("expected_result"),
            actual_result
        )

        return EvalResult(
            question_id=question["id"],
            question=question["question"],
            expected_sql=question.get("expected_sql", ""),
            actual_sql=actual_sql or "",
            sql_match=sql_match,
            expected_result=question.get("expected_result"),
            actual_result=actual_result,
            result_match=result_match,
            steps=steps,
            total_time=total_time,
            success=success,
            error=error or ""
        )

    async def run_all(self, eval_file: Path) -> Dict[str, Any]:
        """运行所有评测"""
        with open(eval_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        questions = data.get("questions", [])
        results = []

        print(f"\n📊 开始评测，共 {len(questions)} 个问题\n")

        for q in questions:
            print(f"📝 执行: {q['id']} - {q['question']}")
            result = await self.run_single(q)
            results.append(result)
            status = "✅" if result.success else "❌"
            print(f"   {status} 耗时: {result.total_time:.2f}s")

        return self._aggregate_results(results)

    def _aggregate_results(self, results: List[EvalResult]) -> Dict[str, Any]:
        """聚合统计结果"""
        total = len(results)
        success = sum(1 for r in results if r.success)
        sql_match = sum(1 for r in results if r.sql_match)
        result_match = sum(1 for r in results if r.result_match)
        avg_time = sum(r.total_time for r in results) / total if total > 0 else 0

        return {
            "total": total,
            "success_count": success,
            "success_rate": success / total if total > 0 else 0,
            "sql_match_count": sql_match,
            "sql_accuracy": sql_match / total if total > 0 else 0,
            "result_match_count": result_match,
            "result_accuracy": result_match / total if total > 0 else 0,
            "avg_time": avg_time,
            "details": [
                {
                    "id": r.question_id,
                    "question": r.question,
                    "success": r.success,
                    "sql_match": r.sql_match,
                    "result_match": r.result_match,
                    "time": r.total_time,
                    "error": r.error
                }
                for r in results
            ]
        }

    def _compare_sql(self, expected: str, actual: str) -> bool:
        """比较 SQL"""
        def normalize(sql):
            if not sql:
                return ""
            return sql.strip().replace("  ", " ").replace("\n", " ").lower()

        return normalize(expected) == normalize(actual)

    def _compare_results(self, expected, actual) -> bool:
        """比较查询结果"""
        if expected is None and actual is None:
            return True
        if expected is None or actual is None:
            return False
        return expected == actual


async def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="运行评测")
    parser.add_argument("questions_file", help="评测问题 JSON 文件路径")
    args = parser.parse_args()

    questions_path = Path(args.questions_file)
    if not questions_path.exists():
        print(f"❌ 文件不存在: {questions_path}")
        return

    runner = EvalRunner()
    await runner.setup()

    if not runner.service:
        print("⚠️ QueryService 未初始化，退出")
        return

    results = await runner.run_all(questions_path)

    # 输出报告
    print("\n" + "=" * 50)
    print("📊 评测报告")
    print("=" * 50)
    print(f"总样本数: {results['total']}")
    print(f"成功率: {results['success_rate']:.2%}")
    print(f"SQL 正确率: {results['sql_accuracy']:.2%}")
    print(f"结果正确率: {results['result_accuracy']:.2%}")
    print(f"平均耗时: {results['avg_time']:.2f}s")
    print("=" * 50)

    # 保存报告
    report_path = Path("eval/reports")
    report_path.mkdir(exist_ok=True)
    report_file = report_path / f"report_{time.strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\n📁 报告已保存: {report_file}")


if __name__ == "__main__":
    asyncio.run(main())