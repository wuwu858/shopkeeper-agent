# app/core/audit.py

from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy import text

from app.clients.mysql_client_manager import meta_mysql_client_manager
from app.core.log import logger


class AuditLogger:
    """审计日志记录器"""

    async def log_query(
            self,
            user_id: str,
            user_name: str,
            query_text: str,
            generated_sql: Optional[str] = None,
            exec_status: str = "pending",
            exec_time: Optional[int] = None,
            return_rows: Optional[int] = None,
            llm_token: Optional[int] = None,
            err_msg: Optional[str] = None,
            ip_address: Optional[str] = None,
            user_agent: Optional[str] = None,
    ):
        """
        记录查询审计日志
        """
        try:
            async with meta_mysql_client_manager.session_factory() as session:
                sql = """
                    INSERT INTO query_audit (
                        user_id, user_name, query_text, generated_sql,
                        exec_status, exec_time, return_rows, llm_token,
                        err_msg, ip_address, user_agent, created_at
                    ) VALUES (
                        :user_id, :user_name, :query_text, :generated_sql,
                        :exec_status, :exec_time, :return_rows, :llm_token,
                        :err_msg, :ip_address, :user_agent, :created_at
                    )
                """
                await session.execute(
                    text(sql),
                    {
                        "user_id": user_id,
                        "user_name": user_name,
                        "query_text": query_text,
                        "generated_sql": generated_sql,
                        "exec_status": exec_status,
                        "exec_time": exec_time,
                        "return_rows": return_rows,
                        "llm_token": llm_token,
                        "err_msg": err_msg,
                        "ip_address": ip_address,
                        "user_agent": user_agent,
                        "created_at": datetime.now(),
                    }
                )
                await session.commit()
                logger.debug(f"📝 审计日志已记录: user={user_id}, status={exec_status}")
        except Exception as e:
            logger.error(f"❌ 审计日志写入失败: {e}")

    async def log_sql_security_denied(
            self,
            user_id: str,
            user_name: str,
            query_text: str,
            generated_sql: str,
            reason: str,
            ip_address: Optional[str] = None,
    ):
        """记录 SQL 安全拦截日志"""
        await self.log_query(
            user_id=user_id,
            user_name=user_name,
            query_text=query_text,
            generated_sql=generated_sql,
            exec_status="denied",
            err_msg=f"SQL安全拦截: {reason}",
            ip_address=ip_address,
        )


# 全局实例
audit_logger = AuditLogger()