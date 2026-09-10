# app/repositories/mysql/meta/mappers/column_info_mapper.py
from app.entities.column_info import ColumnInfo
from app.models.column_info import ColumnInfoMySQL


class ColumnInfoMapper:
    """字段信息映射器"""

    @staticmethod
    def to_entity(model: ColumnInfoMySQL) -> ColumnInfo:
        """将 ORM Model 转换为业务实体"""
        if model is None:
            return None
        return ColumnInfo(
            id=model.id,
            name=model.name,
            type=model.type,
            role=model.role,
            examples=model.examples or [],
            description=model.description,
            alias=model.alias or [],
            table_id=model.table_id,
        )

    # ✅ 添加 to_model 方法
    @staticmethod
    def to_model(entity: ColumnInfo) -> ColumnInfoMySQL:
        """将业务实体转换为 ORM Model"""
        if entity is None:
            return None
        return ColumnInfoMySQL(
            id=entity.id,
            name=entity.name,
            type=entity.type,
            role=entity.role,
            examples=entity.examples or [],
            description=entity.description,
            alias=entity.alias or [],
            table_id=entity.table_id,
        )