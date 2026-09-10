import json
from sqlalchemy import text

from app.entities.column_info import ColumnInfo
from app.entities.table_info import TableInfo
from app.repositories.mysql.meta.mappers.column_info_mapper import ColumnInfoMapper
from app.repositories.mysql.meta.mappers.table_info_mapper import TableInfoMapper


class MetaMySQLRepository:
    def __init__(self, session):
        self.session = session

    async def save_table_infos(self, table_infos: list[TableInfo]):
        for table_info in table_infos:
            model = TableInfoMapper.to_model(table_info)
            stmt = text("""
                INSERT INTO table_info (id, name, role, description)
                VALUES (:id, :name, :role, :description)
                ON DUPLICATE KEY UPDATE
                    name = VALUES(name),
                    role = VALUES(role),
                    description = VALUES(description)
            """)
            await self.session.execute(stmt, {
                "id": model.id,
                "name": model.name,
                "role": model.role,
                "description": model.description
            })
        print(f"✅ 保存 {len(table_infos)} 张表信息")

    async def save_column_infos(self, table_id: str, column_infos: list[ColumnInfo]):
        """保存字段信息到元数据库"""
        for column_info in column_infos:
            model = ColumnInfoMapper.to_model(column_info)
            examples_json = json.dumps(model.examples, ensure_ascii=False) if model.examples else None
            alias_json = json.dumps(model.alias, ensure_ascii=False) if model.alias else None

            stmt = text("""
                INSERT INTO column_info (id, name, type, `role`, examples, description, alias, table_id)
                VALUES (:id, :name, :type, :role, :examples, :description, :alias, :table_id)
                ON DUPLICATE KEY UPDATE
                    name = VALUES(name),
                    type = VALUES(type),
                    `role` = VALUES(`role`),
                    examples = VALUES(examples),
                    description = VALUES(description),
                    alias = VALUES(alias),
                    table_id = VALUES(table_id)
            """)
            await self.session.execute(stmt, {
                "id": model.id,
                "name": model.name,
                "type": model.type,
                "role": model.role,
                "examples": examples_json,
                "description": model.description,
                "alias": alias_json,
                "table_id": table_id
            })
        print(f"✅ 保存 {len(column_infos)} 个字段信息")

    async def save_metric_infos(self, metric_infos):
        """保存指标信息到元数据库"""
        for metric_info in metric_infos:
            # ✅ 使用对象属性访问
            metric_id = f"metric_{metric_info.name}"
            relevant_columns_json = json.dumps(
                getattr(metric_info, 'relevant_columns', []),
                ensure_ascii=False
            )

            stmt = text("""
                INSERT INTO metric_info (id, name, description, relevant_columns)
                VALUES (:id, :name, :description, :relevant_columns)
                ON DUPLICATE KEY UPDATE
                    name = VALUES(name),
                    description = VALUES(description),
                    relevant_columns = VALUES(relevant_columns)
            """)
            await self.session.execute(stmt, {
                "id": metric_id,
                "name": metric_info.name,
                "description": getattr(metric_info, 'description', ''),
                "relevant_columns": relevant_columns_json
            })
        print(f"✅ 保存 {len(metric_infos)} 个指标信息")

    async def save_column_metrics(self, column_metrics):
        """保存字段-指标关联关系"""
        for cm in column_metrics:
            stmt = text("""
                INSERT INTO column_metric (column_id, metric_id)
                VALUES (:column_id, :metric_id)
                ON DUPLICATE KEY UPDATE column_id = column_id
            """)
            await self.session.execute(stmt, {
                "column_id": cm.column_id,
                "metric_id": cm.metric_id
            })
        print(f"✅ 保存 {len(column_metrics)} 个字段-指标关联")

    async def get_column_info_by_id(self, id: str):
        """按字段 id 查询字段元数据"""
        from app.models.column_info import ColumnInfoMySQL
        from app.repositories.mysql.meta.mappers.column_info_mapper import ColumnInfoMapper

        column_info: ColumnInfoMySQL | None = await self.session.get(ColumnInfoMySQL, id)
        if column_info:
            return ColumnInfoMapper.to_entity(column_info)
        return None

    async def get_table_info_by_id(self, id: str):
        """按表 id 查询表元数据"""
        from app.models.table_info import TableInfoMySQL
        from app.repositories.mysql.meta.mappers.table_info_mapper import TableInfoMapper

        table_info: TableInfoMySQL | None = await self.session.get(TableInfoMySQL, id)
        if table_info:
            return TableInfoMapper.to_entity(table_info)
        return None

    async def get_key_columns_by_table_id(self, table_id: str) -> list:
        """查询指定表的主外键字段"""
        sql = "select * from column_info where table_id = :table_id and role in ('primary_key','foreign_key')"
        result = await self.session.execute(text(sql), {"table_id": table_id})
        return [ColumnInfo(**dict(row)) for row in result.mappings().fetchall()]