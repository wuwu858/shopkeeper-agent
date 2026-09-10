from langgraph.runtime import Runtime

from app.agent.context import DataAgentContext
from app.agent.state import DataAgentState
from app.core.log import logger


async def recall_value(state: DataAgentState, runtime: Runtime[DataAgentContext]):
    step = "召回字段取值"
    writer = runtime.stream_writer

    writer({"type": "progress", "step": step, "status": "running"})

    try:
        query = state["query"]
        keywords = state["keywords"]

        value_es_repository = runtime.context["value_es_repository"]

        # 全文检索字段取值
        results = await value_es_repository.search(query, limit=5)

        retrieved_value_infos = results

        logger.info(f"检索到字段取值：{[value.id for value in retrieved_value_infos]}")
        writer({"type": "progress", "step": step, "status": "success"})
        return {"retrieved_value_infos": retrieved_value_infos}
    except Exception as e:
        logger.error(f"{step} failed: {e}")
        writer({"type": "progress", "step": step, "status": "error"})
        raise