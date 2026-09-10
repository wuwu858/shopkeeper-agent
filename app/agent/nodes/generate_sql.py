# app/agent/nodes/generate_sql.py

import yaml
import re
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate
from langgraph.runtime import Runtime

from app.agent.context import DataAgentContext
from app.agent.llm import llm
from app.agent.state import DataAgentState
from app.core.log import logger
from app.prompt.prompt_loader import load_prompt

# ==================== 辅助函数 ====================

# MySQL 保留关键字列表
MYSQL_RESERVED_KEYWORDS = {
    'order', 'group', 'where', 'select', 'from', 'join',
    'table', 'index', 'database', 'schema', 'column',
    'procedure', 'function', 'trigger', 'view', 'show',
    'values', 'insert', 'update', 'delete',
    'create', 'alter', 'drop', 'rename', 'truncate',
    'by', 'as', 'on', 'and', 'or', 'not', 'null', 'true', 'false',
    'primary', 'key', 'foreign', 'references', 'constraint',
    'check', 'default', 'unique', 'index', 'fulltext', 'spatial'
}

DEFAULT_LIMIT = 1000
MAX_LIMIT = 10000


def escape_mysql_identifier(name: str) -> str:
    """转义 MySQL 标识符"""
    if not name:
        return name
    if name.startswith('`') and name.endswith('`'):
        return name
    if name.lower() in MYSQL_RESERVED_KEYWORDS:
        return f"`{name}`"
    if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', name):
        return f"`{name}`"
    return name


def fix_sql_identifiers(sql: str) -> str:
    """修复 SQL 中的标识符"""
    if not sql:
        return sql

    table_pattern = r'(FROM|JOIN|INTO|UPDATE)\s+([a-zA-Z_][a-zA-Z0-9_.]*)'

    def replace_table(match):
        keyword = match.group(1)
        table_name = match.group(2)
        if '.' in table_name:
            parts = table_name.split('.')
            escaped_parts = [escape_mysql_identifier(p) for p in parts]
            return f"{keyword} {'.'.join(escaped_parts)}"
        return f"{keyword} {escape_mysql_identifier(table_name)}"

    sql = re.sub(table_pattern, replace_table, sql, flags=re.IGNORECASE)

    order_pattern = r'(ORDER BY|GROUP BY)\s+([a-zA-Z_][a-zA-Z0-9_]*)'

    def replace_order_column(match):
        keyword = match.group(1)
        column_name = match.group(2)
        return f"{keyword} {escape_mysql_identifier(column_name)}"

    sql = re.sub(order_pattern, replace_order_column, sql, flags=re.IGNORECASE)

    return sql


def add_limit_if_missing(sql: str, default_limit: int = DEFAULT_LIMIT) -> str:
    """如果 SQL 没有 LIMIT，自动添加"""
    if not sql:
        return sql

    sql_upper = sql.upper()
    limit_pattern = r'LIMIT\s+(\d+)'
    match = re.search(limit_pattern, sql_upper)

    if match:
        try:
            limit_val = int(match.group(1))
            if limit_val > MAX_LIMIT:
                logger.warning(f"⚠️ LIMIT {limit_val} 超过上限 {MAX_LIMIT}，自动截断")
                sql = re.sub(limit_pattern, f'LIMIT {MAX_LIMIT}', sql, flags=re.IGNORECASE)
        except ValueError:
            pass
        return sql

    sql = sql.rstrip(';')
    sql = sql + f' LIMIT {default_limit}'
    logger.info(f"✅ 自动添加 LIMIT: {default_limit}")
    return sql


def extract_last_sql_from_history(state: DataAgentState) -> str:
    """从对话历史中提取最后一次执行的 SQL"""
    history = state.get("history", [])
    for msg in reversed(history):
        if msg.get("role") == "assistant" and msg.get("sql"):
            return msg.get("sql")
    return ""


def build_context_for_sql(state: DataAgentState) -> tuple[str, str]:
    """构建 SQL 生成的上下文"""
    compressed_context = state.get("compressed_context", "")
    last_sql = state.get("last_sql", "")
    if not last_sql:
        last_sql = extract_last_sql_from_history(state)
    return compressed_context, last_sql


# ==================== 主节点 ====================

async def generate_sql(state: DataAgentState, runtime: Runtime[DataAgentContext]):
    """生成 SQL 语句（支持多轮对话 + 字典）"""
    step = "生成SQL"
    writer = runtime.stream_writer

    writer({"type": "progress", "step": step, "status": "running"})

    try:
        table_infos = state.get("table_infos", [])
        metric_infos = state.get("metric_infos", [])
        date_info = state.get("date_info", {})
        db_info = state.get("db_info", {})
        query = state.get("query", "")

        # ✅ 获取字典上下文
        dict_context = state.get("dictionary_context", {})
        metric_dict = dict_context.get("metrics", {})
        dimension_dict = dict_context.get("dimensions", {})
        region_mapping = dict_context.get("region_mapping", {})

        if not table_infos:
            logger.warning("没有表信息，无法生成 SQL")
            writer({"type": "progress", "step": step, "status": "error"})
            return {"sql": "", "error": "没有可用的表信息"}

        # ✅ 获取多轮对话上下文
        history = state.get("history", [])
        turn = len([msg for msg in history if msg.get("role") == "user"])
        compressed_context, last_sql = build_context_for_sql(state)

        # ✅ 选择提示词
        if turn >= 1 and compressed_context:
            logger.info(f"📝 多轮对话（第 {turn} 轮），使用上下文提示词")
            prompt_template = load_prompt("generate_sql_with_context")
            input_vars = [
                "table_infos", "metric_infos", "date_info", "db_info", "query",
                "compressed_context", "last_sql",
                "metric_dict", "dimension_dict", "region_mapping"
            ]
            prompt = PromptTemplate(template=prompt_template, input_variables=input_vars)

            result = await _generate_with_context_dict(
                prompt, query, table_infos, metric_infos,
                date_info, db_info, compressed_context, last_sql,
                metric_dict, dimension_dict, region_mapping
            )
        else:
            logger.info("📝 首轮对话，使用标准提示词")
            prompt = PromptTemplate(
                template=load_prompt("generate_sql"),
                input_variables=[
                    "table_infos", "metric_infos", "date_info", "db_info", "query",
                    "metric_dict", "dimension_dict", "region_mapping"
                ],
            )

            result = await _generate_normal_dict(
                prompt, query, table_infos, metric_infos,
                date_info, db_info, metric_dict, dimension_dict, region_mapping
            )

        # ✅ 清理和修复 SQL
        cleaned_sql = result.strip()
        cleaned_sql = re.sub(r'^```sql\s*', '', cleaned_sql)
        cleaned_sql = re.sub(r'\s*```$', '', cleaned_sql)
        cleaned_sql = cleaned_sql.strip()

        fixed_sql = fix_sql_identifiers(cleaned_sql)
        fixed_sql = add_limit_if_missing(fixed_sql)

        logger.info(f"生成的SQL：{fixed_sql[:200]}...")
        writer({"type": "progress", "step": step, "status": "success"})

        return {"sql": fixed_sql, "last_sql": fixed_sql,"error": ""}

    except Exception as e:
        logger.error(f"{step} failed: {e}", exc_info=True)
        writer({"type": "progress", "step": step, "status": "error"})
        return {"sql": "", "error": str(e)}


# ==================== 生成函数 ====================

async def _generate_normal_dict(
        prompt: PromptTemplate,
        query: str,
        table_infos: list,
        metric_infos: list,
        date_info: dict,
        db_info: dict,
        metric_dict: dict,
        dimension_dict: dict,
        region_mapping: dict
) -> str:
    """标准 SQL 生成（含字典）"""
    output_parser = StrOutputParser()
    chain = prompt | llm | output_parser

    return await chain.ainvoke({
        "table_infos": yaml.dump(table_infos, allow_unicode=True, sort_keys=False),
        "metric_infos": yaml.dump(metric_infos, allow_unicode=True, sort_keys=False),
        "date_info": yaml.dump(date_info, allow_unicode=True, sort_keys=False),
        "db_info": yaml.dump(db_info, allow_unicode=True, sort_keys=False),
        "query": query,
        "metric_dict": yaml.dump(metric_dict, allow_unicode=True, sort_keys=False) if metric_dict else "无",
        "dimension_dict": yaml.dump(dimension_dict, allow_unicode=True, sort_keys=False) if dimension_dict else "无",
        "region_mapping": yaml.dump(region_mapping, allow_unicode=True, sort_keys=False) if region_mapping else "无",
    })


async def _generate_with_context_dict(
        prompt: PromptTemplate,
        query: str,
        table_infos: list,
        metric_infos: list,
        date_info: dict,
        db_info: dict,
        compressed_context: str,
        last_sql: str,
        metric_dict: dict,
        dimension_dict: dict,
        region_mapping: dict
) -> str:
    """带上下文的 SQL 生成（含字典）"""
    output_parser = StrOutputParser()
    chain = prompt | llm | output_parser

    return await chain.ainvoke({
        "table_infos": yaml.dump(table_infos, allow_unicode=True, sort_keys=False),
        "metric_infos": yaml.dump(metric_infos, allow_unicode=True, sort_keys=False),
        "date_info": yaml.dump(date_info, allow_unicode=True, sort_keys=False),
        "db_info": yaml.dump(db_info, allow_unicode=True, sort_keys=False),
        "query": query,
        "compressed_context": compressed_context or "无历史对话",
        "last_sql": last_sql or "无",
        "metric_dict": yaml.dump(metric_dict, allow_unicode=True, sort_keys=False) if metric_dict else "无",
        "dimension_dict": yaml.dump(dimension_dict, allow_unicode=True, sort_keys=False) if dimension_dict else "无",
        "region_mapping": yaml.dump(region_mapping, allow_unicode=True, sort_keys=False) if region_mapping else "无",
    })