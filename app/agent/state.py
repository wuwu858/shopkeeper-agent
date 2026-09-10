from typing import TypedDict, List, Dict, Any, Optional
from datetime import datetime

from app.entities.column_info import ColumnInfo
from app.entities.metric_info import MetricInfo
from app.entities.value_info import ValueInfo


class MetricInfoState(TypedDict):
    name: str
    description: str
    relevant_columns: list[str]
    alias: list[str]


class ColumnInfoState(TypedDict):
    name: str
    type: str
    role: str
    examples: list
    description: str
    alias: list[str]


class TableInfoState(TypedDict):
    name: str
    role: str
    description: str
    columns: list[ColumnInfoState]


class DateInfoState(TypedDict):
    date: str
    weekday: str
    quarter: str


class DBInfoState(TypedDict):
    dialect: str
    version: str


class DictionaryContextState(TypedDict):
    """字典上下文"""
    metrics: Dict[str, Any]  # 指标字典
    dimensions: Dict[str, Any]  # 维度字典
    region_mapping: Dict[str, List[str]]  # 地区映射


# ✅ 新增：单条对话消息
class Message(TypedDict):
    """单条对话消息"""
    role: str  # "user" 或 "assistant"
    content: str
    sql: Optional[str]  # 如果是 assistant 且有 SQL，记录
    result: Optional[Any]  # 如果是 assistant 且有查询结果，记录
    timestamp: str  # ISO 格式时间


class DataAgentState(TypedDict):
    # === 原有字段 ===
    query: str
    keywords: list[str]

    retrieved_column_infos: list[ColumnInfo]
    retrieved_metric_infos: list[MetricInfo]
    retrieved_value_infos: list[ValueInfo]

    table_infos: list[TableInfoState]
    metric_infos: list[MetricInfoState]

    date_info: DateInfoState
    db_info: DBInfoState

    sql: str
    error: str

    # === ✅ 新增：多轮对话相关字段 ===

    # 对话历史列表
    history: List[Message]

    # 当前会话 ID（用于追踪整个对话链路）
    session_id: str

    # 压缩后的上下文摘要（由 compress_context 节点生成）
    compressed_context: str

    # 上一次执行的 SQL（从历史中提取，方便快速访问）
    last_sql: str

    # 当前对话轮次（从 0 开始）
    turn: int

    # 是否需要压缩上下文（由前置节点判断设置）
    need_compression: bool

    # === ✅ 新增：字典上下文 ===
    dictionary_context: Optional[DictionaryContextState]  # 业务字典上下文