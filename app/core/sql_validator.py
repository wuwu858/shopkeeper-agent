# app/core/sql_validator.py

import re
import sqlglot
from sqlglot import parse_one
from sqlglot.errors import ParseError
from typing import Tuple, Optional, Dict, Any

from app.core.log import logger


class SQLSecurityValidator:
    """
    SQL 安全校验器

    功能：
    1. 只允许 SELECT 查询
    2. 禁止 SELECT *
    3. 强制带 LIMIT
    4. 检查敏感列
    5. 添加行级权限
    6. 危险关键字拦截（增强）
    """

    # 禁止的 SQL 操作
    FORBIDDEN_COMMANDS = {
        'INSERT', 'UPDATE', 'DELETE',
        'DROP', 'ALTER', 'CREATE',
        'TRUNCATE', 'GRANT', 'REVOKE',
        'REPLACE', 'RENAME',
        'CALL', 'EXECUTE', 'EXEC',
        'LOAD', 'INTO', 'OUTFILE',
        'SHUTDOWN', 'KILL',
        'REINDEX', 'VACUUM',
    }

    # ✅ 新增：危险关键字模式（用于正则匹配）
    DANGEROUS_PATTERNS = [
        r'\bDROP\s+(DATABASE|SCHEMA|TABLE|INDEX|VIEW|PROCEDURE|FUNCTION|TRIGGER)\b',
        r'\bDELETE\s+FROM\b',
        r'\bTRUNCATE\s+TABLE\b',
        r'\bALTER\s+TABLE\b',
        r'\bCREATE\s+(DATABASE|SCHEMA|TABLE|INDEX|VIEW)\b',
        r'\bINSERT\s+INTO\b',
        r'\bUPDATE\s+\w+\s+SET\b',
        r'\bGRANT\b',
        r'\bREVOKE\b',
        r'\bCALL\b',
        r'\bEXEC(UTE)?\b',
        r'\bLOAD\s+(DATA|FILE)\b',
        r'\bINTO\s+OUTFILE\b',
        r'\bSHUTDOWN\b',
        r'\bKILL\b',
        r'\bRENAME\s+TABLE\b',
        r'\bREINDEX\b',
    ]

    # 敏感列
    SENSITIVE_COLUMNS = {
        'cost_price': '成本价',
        'profit_margin': '利润率',
        'customer_phone': '客户电话',
        'customer_id_card': '客户身份证',
        'staff_salary': '员工薪资',
        'password': '密码',
        'token': 'Token',
        'secret': '密钥',
    }

    def __init__(self, max_limit: int = 10000, query_timeout: int = 30):
        self.max_limit = max_limit
        self.query_timeout = query_timeout

    async def validate(
            self,
            sql: str,
            user_info: Optional[Dict[str, Any]] = None
    ) -> Tuple[bool, str]:
        """
        校验 SQL 安全性

        Returns:
            (is_valid, message_or_sql)
        """
        # ✅ 1. 危险关键字拦截（最高优先级）
        is_valid, msg = self._check_dangerous_keywords(sql)
        if not is_valid:
            logger.warning(f"⚠️ 危险 SQL 被拦截: {sql[:100]}...")
            return False, msg

        # 2. 基本安全检查
        is_valid, msg = await self._basic_security_check(sql)
        if not is_valid:
            return False, msg

        # 3. 解析 SQL
        try:
            parsed = parse_one(sql)
        except ParseError as e:
            logger.error(f"SQL 解析失败: {e}")
            return False, f"SQL 语法错误: {e}"

        # 4. 检查命令类型
        is_valid, msg = self._check_command_type(parsed)
        if not is_valid:
            return False, msg

        # 5. 检查 SELECT *
        is_valid, msg = self._check_select_star(parsed)
        if not is_valid:
            return False, msg

        # 6. 检查 LIMIT
        is_valid, msg = self._check_limit(parsed)
        if not is_valid:
            return False, msg

        # 7. 检查敏感列
        is_valid, msg = self._check_sensitive_columns(parsed, user_info)
        if not is_valid:
            return False, msg

        # 8. 添加行级权限
        if user_info and user_info.get('regions'):
            sql = await self._apply_row_permission(sql, user_info)

        return True, sql

    def _check_dangerous_keywords(self, sql: str) -> Tuple[bool, str]:
        """✅ 危险关键字拦截"""
        sql_upper = sql.upper()

        for pattern in self.DANGEROUS_PATTERNS:
            if re.search(pattern, sql_upper, re.IGNORECASE):
                return False, f"检测到危险 SQL 操作: {pattern}"

        return True, "通过"

    async def _basic_security_check(self, sql: str) -> Tuple[bool, str]:
        """基本安全检查：危险关键字"""
        sql_upper = sql.upper()

        for cmd in self.FORBIDDEN_COMMANDS:
            if re.search(rf'\b{cmd}\b', sql_upper):
                return False, f"禁止执行 {cmd} 操作"

        return True, "基本安全检查通过"

    @staticmethod
    def _check_command_type(parsed) -> Tuple[bool, str]:
        """检查是否只包含 SELECT"""
        try:
            # sqlglot 的 keyword 属性
            if hasattr(parsed, 'key'):
                stmt_type = parsed.key
            elif hasattr(parsed, 'keyword'):
                stmt_type = parsed.keyword
            else:
                stmt_type = str(parsed)[:20]

            if stmt_type.upper() not in ['SELECT', 'EXPLAIN']:
                return False, f"只允许 SELECT 查询，当前为 {stmt_type}"
            return True, ""
        except Exception:
            return False, "无法解析 SQL 类型"

    @staticmethod
    def _check_select_star(parsed) -> Tuple[bool, str]:
        """检查是否使用了 SELECT *"""
        try:
            for node in parsed.find_all(sqlglot.expressions.Column):
                if node.name == '*':
                    return False, "禁止使用 SELECT *，请明确指定字段"
            return True, ""
        except Exception:
            return True, ""

    @staticmethod
    def _check_limit(parsed, max_limit: int = 10000) -> Tuple[bool, str]:
        """检查是否有 LIMIT 且值不超过限制"""
        try:
            for node in parsed.find_all(sqlglot.expressions.Limit):
                if node.expression:
                    try:
                        limit_val = int(node.expression.name)
                        if limit_val > max_limit:
                            return False, f"LIMIT 不能超过 {max_limit}，当前为 {limit_val}"
                        return True, ""
                    except (ValueError, AttributeError):
                        pass
                else:
                    return False, "LIMIT 需要指定具体数值"

            return False, "大表查询必须带 LIMIT（建议不超过 1000）"
        except Exception:
            return True, ""

    @staticmethod
    def _check_sensitive_columns(
            parsed,
            user_info: Optional[Dict[str, Any]] = None
    ) -> Tuple[bool, str]:
        """检查是否查询了敏感列"""
        try:
            role = user_info.get('role', 'viewer') if user_info else 'viewer'

            # 从数据库获取敏感列配置（使用类变量）
            sensitive_cols = SQLSecurityValidator.SENSITIVE_COLUMNS

            for node in parsed.find_all(sqlglot.expressions.Column):
                col_name = node.name
                if col_name in sensitive_cols:
                    if role not in ['admin', 'manager']:
                        return False, f"禁止查询敏感列: {col_name} ({sensitive_cols[col_name]})"

            return True, ""
        except Exception:
            return True, ""

    @staticmethod
    async def _apply_row_permission(
            sql: str,
            user_info: Dict[str, Any]
    ) -> str:
        """添加行级权限过滤"""
        regions = user_info.get('regions', [])
        if not regions:
            return sql

        # 使用列表推导式构建条件
        quoted_regions = [f'"{r}"' for r in regions]
        region_condition = "region IN ({})".format(", ".join(quoted_regions))

        sql_upper = sql.upper()
        if "WHERE" in sql_upper:
            # 已有 WHERE，追加条件
            sql = sql.replace("WHERE", f"WHERE {region_condition} AND")
        else:
            # 在第一个 FROM 后添加
            pattern = r'(FROM\s+\S+)'
            sql = re.sub(
                pattern,
                rf'\1 WHERE {region_condition}',
                sql,
                flags=re.IGNORECASE
            )

        logger.info(f"添加行级权限: {region_condition}")
        return sql


# 全局单例
sql_validator = SQLSecurityValidator()