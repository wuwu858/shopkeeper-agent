from langgraph.runtime import Runtime

from app.agent.context import DataAgentContext
from app.agent.state import DataAgentState
from app.core.log import logger


async def recall_metric(state: DataAgentState, runtime: Runtime[DataAgentContext]):
    step = "召回指标信息"
    writer = runtime.stream_writer

    writer({"type": "progress", "step": step, "status": "running"})

    try:
        query = state["query"]

        metric_qdrant_repository = runtime.context["metric_qdrant_repository"]
        embedding_client = runtime.context["embedding_client"]

        query_vector = await embedding_client.aembed_query(query)

        results = await metric_qdrant_repository.search(query_vector, limit=10)

        # ✅ 去重：根据指标名称去重
        seen = set()
        unique_results = []
        for result in results:
            # 假设 result 是 MetricInfo 对象
            metric_name = result.name if hasattr(result, 'name') else result.get('name')
            if metric_name not in seen:
                seen.add(metric_name)
                unique_results.append(result)

        retrieved_metric_infos = unique_results

        logger.info(f"检索到指标信息：{[metric.name for metric in retrieved_metric_infos]}")
        writer({"type": "progress", "step": step, "status": "success"})
        return {"retrieved_metric_infos": retrieved_metric_infos}
    except Exception as e:
        logger.error(f"{step} failed: {e}")
        writer({"type": "progress", "step": step, "status": "error"})
        raise