# app/repositories/mysql/dw/dw_mysql_repository.py

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, List, Optional


class DWMySQLRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_db_info(self) -> Dict[str, str]:
        """获取数据库信息"""
        try:
            sql = "SELECT VERSION()"
            result = await self.session.execute(text(sql))
            version = result.scalar()

            # 获取数据库名称
            db_sql = "SELECT DATABASE()"
            db_result = await self.session.execute(text(db_sql))
            db_name = db_result.scalar()

            return {
                "dialect": "mysql",
                "version": version or "8.0.46",
                "database": db_name or "dw"
            }
        except Exception as e:
            print(f"❌ 获取数据库信息失败: {e}")
            return {
                "dialect": "mysql",
                "version": "8.0.46",
                "database": "dw"
            }

    async def validate(self, sql: str) -> bool:
        """
        使用 EXPLAIN 校验 SQL 语法

        Args:
            sql: 要校验的 SQL

        Returns:
            True: 语法正确
            Raises: 如果语法错误会抛出异常
        """
        try:
            # 使用 EXPLAIN 检查 SQL 语法
            explain_sql = f"EXPLAIN {sql}"
            await self.session.execute(text(explain_sql))
            return True
        except Exception as e:
            raise Exception(f"SQL 语法错误: {e}")

    async def run(self, sql: str) -> list[dict]:
        """执行 SQL 并返回结果"""
        try:
            result = await self.session.execute(text(sql))
            return [dict(row) for row in result.mappings().fetchall()]
        except Exception as e:
            raise Exception(f"SQL 执行失败: {e}")

    async def get_column_types(self, table_name: str) -> Dict[str, Dict]:
        """获取表的字段类型信息"""
        sql = """
            SELECT 
                COLUMN_NAME,
                DATA_TYPE,
                IS_NULLABLE,
                COLUMN_DEFAULT,
                COLUMN_KEY
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE()
            AND TABLE_NAME = :table_name
            ORDER BY ORDINAL_POSITION
        """
        try:
            result = await self.session.execute(text(sql), {"table_name": table_name})
            rows = result.fetchall()

            column_types = {}
            for row in rows:
                column_types[row[0]] = {
                    "data_type": row[1],
                    "is_nullable": row[2] == 'YES',
                    "default": row[3],
                    "is_primary": row[4] == 'PRI'
                }

            return column_types

        except Exception as e:
            print(f"❌ 获取表 {table_name} 的字段类型失败: {e}")
            return {}

    async def get_column_values(self, table_name: str, column_name: str, limit: int = 100) -> List[str]:
        """获取表中指定字段的去重取值"""
        sql = f"""
            SELECT DISTINCT {column_name}
            FROM {table_name}
            WHERE {column_name} IS NOT NULL
            AND {column_name} != ''
            LIMIT :limit
        """
        try:
            result = await self.session.execute(text(sql), {"limit": limit})
            rows = result.fetchall()
            return [str(row[0]) for row in rows if row[0] is not None]

        except Exception as e:
            print(f"❌ 获取表 {table_name} 字段 {column_name} 的取值失败: {e}")
            return []