# app/agent/nodes/run_sql.py（更新版 - 方案1）

from datetime import datetime
from langgraph.runtime import Runtime

from app.agent.context import DataAgentContext
from app.agent.state import DataAgentState
from app.core.log import logger
from app.core.sql_validator import sql_validator
from app.core.audit import audit_logger
import time


async def run_sql(state: DataAgentState, runtime: Runtime[DataAgentContext]):
    """
    执行 SQL 节点（带安全校验 + 审计日志）
    方案1：只存正确的 SQL，错误的 SQL 不存入历史
    """
    step = "执行SQL"
    writer = runtime.stream_writer
    start_time = time.time()

    writer({"type": "progress", "step": step, "status": "running"})

    # 获取用户信息
    user_info = state.get("user_info", {})
    user_id = user_info.get("user_id", "unknown")
    user_name = user_info.get("username", "unknown")
    query_text = state.get("query", "")
    sql = state.get("sql", "")

    try:
        if not sql:
            raise ValueError("SQL 语句为空，无法执行")

        # ✅ 1. SQL 安全校验
        is_valid, result = await sql_validator.validate(sql, user_info)
        if not is_valid:
            logger.warning(f"❌ SQL 安全校验失败: {result}")

            # 记录审计日志（拦截）
            await audit_logger.log_sql_security_denied(
                user_id=user_id,
                user_name=user_name,
                query_text=query_text,
                generated_sql=sql,
                reason=result,
            )

            writer({"type": "error", "message": f"SQL 安全校验失败: {result}"})
            return {"error": result}

        safe_sql = result

        dw_mysql_repository = runtime.context["dw_mysql_repository"]

        # ✅ 2. 记录审计日志（执行前）
        await audit_logger.log_query(
            user_id=user_id,
            user_name=user_name,
            query_text=query_text,
            generated_sql=safe_sql,
            exec_status="pending",
        )

        # ✅ 3. 执行 SQL
        logger.info(f"执行 SQL: {safe_sql[:100]}..." if len(safe_sql) > 100 else f"执行 SQL: {safe_sql}")
        result_data = await dw_mysql_repository.run(safe_sql)

        exec_time = int((time.time() - start_time) * 1000)

        # ✅ 4. 记录审计日志（成功）
        await audit_logger.log_query(
            user_id=user_id,
            user_name=user_name,
            query_text=query_text,
            generated_sql=safe_sql,
            exec_status="success",
            exec_time=exec_time,
            return_rows=len(result_data),
        )

        logger.info(f"SQL 执行成功，影响 {len(result_data)} 条记录")

        # ✅ ===== 方案1：只存正确 SQL =====
        history = state.get("history", [])
        history.append({
            "role": "user",
            "content": query_text,
            "timestamp": datetime.now().isoformat()
        })
        # ✅ 只有成功才存 SQL，且存的是经过校验的 safe_sql
        history.append({
            "role": "assistant",
            "content": f"查询结果：{result_data}" if result_data else "查询完成，无数据返回",
            "sql": safe_sql,  # ✅ 存正确 SQL
            "result": result_data,
            "is_success": True,  # ✅ 标记为成功
            "timestamp": datetime.now().isoformat()
        })

        if len(history) > 50:
            history = history[-50:]

        logger.info(f"📝 对话历史已保存，当前共 {len(history)} 条消息")

        writer({"type": "progress", "step": step, "status": "success"})
        writer({"type": "result", "data": result_data})

        return {"history": history}

    except Exception as e:
        error_msg = str(e)
        exec_time = int((time.time() - start_time) * 1000)

        logger.error(f"{step} 执行失败: {error_msg}")

        # ✅ 记录审计日志（失败）
        await audit_logger.log_query(
            user_id=user_id,
            user_name=user_name,
            query_text=query_text,
            generated_sql=sql,
            exec_status="error",
            exec_time=exec_time,
            err_msg=error_msg,
        )

        # ✅ ===== 方案1：错误时只存错误信息，不存 SQL =====
        try:
            history = state.get("history", [])
            history.append({
                "role": "user",
                "content": query_text,
                "timestamp": datetime.now().isoformat()
            })
            # ✅ 错误消息不存 SQL，标记为错误
            history.append({
                "role": "assistant",
                "content": f"❌ 执行失败: {error_msg}",
                "sql": "",  # ✅ 不存错误 SQL
                "error": error_msg,
                "is_success": False,  # ✅ 标记为失败
                "timestamp": datetime.now().isoformat()
            })
            return {"history": history}
        except:
            pass

        writer({"type": "progress", "step": step, "status": "error"})
        raise