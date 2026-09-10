# app/agent/nodes/recall_column.py

from langgraph.runtime import Runtime

from app.agent.context import DataAgentContext
from app.agent.state import DataAgentState
from app.core.log import logger


async def recall_column(state: DataAgentState, runtime: Runtime[DataAgentContext]):
    step = "召回字段信息"
    writer = runtime.stream_writer

    writer({"type": "progress", "step": step, "status": "running"})

    try:
        query = state["query"]

        # 从上下文获取依赖
        column_qdrant_repository = runtime.context["column_qdrant_repository"]
        embedding_client = runtime.context["embedding_client"]

        # 使用 aembed_query 异步方法
        query_vector = await embedding_client.aembed_query(query)

        # 向量检索
        results = await column_qdrant_repository.search(query_vector, limit=5)

        # 直接使用 results，不需要 .payload
        retrieved_column_infos = results

        logger.info(f"检索到字段信息：{[column.id for column in retrieved_column_infos]}")
        writer({"type": "progress", "step": step, "status": "success"})
        return {"retrieved_column_infos": retrieved_column_infos}
    except Exception as e:
        logger.error(f"{step} failed: {e}")
        writer({"type": "progress", "step": step, "status": "error"})
        raise