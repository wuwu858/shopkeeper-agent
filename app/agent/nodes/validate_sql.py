from langgraph.runtime import Runtime

from app.agent.context import DataAgentContext
from app.agent.state import DataAgentState
from app.core.log import logger


async def validate_sql(state: DataAgentState, runtime: Runtime[DataAgentContext]):
    """校验 SQL 语法是否正确"""

    writer = runtime.stream_writer
    step = "校验SQL"

    writer({"type": "progress", "step": step, "status": "running"})

    sql = state.get("sql", "")  # ✅ 使用 get 防止 KeyError
    dw_mysql_repository = runtime.context["dw_mysql_repository"]

    try:
        await dw_mysql_repository.validate(sql)
        logger.info("SQL语法正确")
        writer({"type": "progress", "step": step, "status": "success"})
        # ✅ 验证通过：保留 sql，error 设为空字符串
        return {"sql": sql, "error": ""}
    except Exception as e:
        error_msg = str(e)
        logger.info(f"SQL语法错误：{error_msg}")
        writer({"type": "progress", "step": step, "status": "error"})
        # ✅ 验证失败：保留 sql 供 correct_sql 使用，同时传递 error
        return {"sql": sql, "error": error_msg}