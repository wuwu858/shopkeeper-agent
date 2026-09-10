# app/repositories/mysql/meta/mappers/table_info_mapper.py
from app.entities.table_info import TableInfo
from app.models.table_info import TableInfoMySQL


class TableInfoMapper:
    """表信息映射器"""

    @staticmethod
    def to_entity(model: TableInfoMySQL) -> TableInfo:
        """将 ORM Model 转换为业务实体"""
        if model is None:
            return None
        return TableInfo(
            id=model.id,
            name=model.name,
            role=model.role,
            description=model.description,
        )

    # ✅ 添加 to_model 方法
    @staticmethod
    def to_model(entity: TableInfo) -> TableInfoMySQL:
        """将业务实体转换为 ORM Model"""
        if entity is None:
            return None
        return TableInfoMySQL(
            id=entity.id,
            name=entity.name,
            role=entity.role,
            description=entity.description,
        )