# app/agent/nodes/correct_sql.py（更新版）

import re
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate
from langgraph.runtime import Runtime

from app.agent.context import DataAgentContext
from app.agent.llm import llm
from app.agent.state import DataAgentState
from app.core.log import logger
from app.prompt.prompt_loader import load_prompt
from app.core.sql_validator import sql_validator

# ✅ 危险 SQL 拦截模式
DANGEROUS_PATTERNS = [
    r'\bDROP\b',
    r'\bDELETE\b',
    r'\bTRUNCATE\b',
    r'\bALTER\b',
    r'\bCREATE\b',
    r'\bINSERT\b',
    r'\bUPDATE\b',
    r'\bGRANT\b',
    r'\bREVOKE\b',
    r'\bCALL\b',
    r'\bEXEC(UTE)?\b',
    r'\bLOAD\s+(DATA|FILE)\b',
    r'\bINTO\s+OUTFILE\b',
    r'\bSHUTDOWN\b',
    r'\bKILL\b',
]


def is_safe_sql(sql: str) -> bool:
    """检查 SQL 是否安全"""
    if not sql:
        return False
    sql_upper = sql.upper()
    for pattern in DANGEROUS_PATTERNS:
        if re.search(pattern, sql_upper):
            return False
    return True


# ✅ ===== 新增：自动修正表关联 =====
def fix_wrong_join(sql: str) -> str:
    """
    自动修正错误的表关联：
    1. province 关联 → region_id 关联
    2. 正确处理表别名和表名
    """
    if not sql:
        return sql

    original_sql = sql

    # ✅ 提取表别名（兼容 dw. 前缀和无别名情况）
    from_match = re.search(r'FROM\s+(?:dw\.)?fact_order(?:\s+(\w+))?', sql, re.IGNORECASE)
    dim_match = re.search(r'JOIN\s+(?:dw\.)?dim_region(?:\s+(\w+))?', sql, re.IGNORECASE)

    fact_alias = from_match.group(1) if from_match and from_match.group(1) else 'fact_order'
    dim_alias = dim_match.group(1) if dim_match and dim_match.group(1) else 'dim_region'

    logger.info(f"📝 检测到别名: fact_order → {fact_alias}, dim_region → {dim_alias}")

    # ✅ 检测错误模式：ON xxx.province = xxx.province
    pattern1 = r'(ON|and)\s+(\w+)\.province\s*=\s*(\w+)\.province'

    if re.search(pattern1, sql, re.IGNORECASE):
        correct_join = f'ON {fact_alias}.region_id = {dim_alias}.region_id'
        sql = re.sub(
            pattern1,
            correct_join,
            sql,
            flags=re.IGNORECASE
        )
        logger.info(f"✅ 自动修正: province → region_id (别名: {fact_alias}, {dim_alias})")

    # ✅ 替换表名+字段为别名+字段（确保使用正确的别名）
    if 'fact_order.region_id' in sql.lower() and fact_alias != 'fact_order':
        sql = sql.replace('fact_order.region_id', f'{fact_alias}.region_id')
        logger.info(f"✅ 自动修正: fact_order.region_id → {fact_alias}.region_id")

    if 'dim_region.region_id' in sql.lower() and dim_alias != 'dim_region':
        sql = sql.replace('dim_region.region_id', f'{dim_alias}.region_id')
        logger.info(f"✅ 自动修正: dim_region.region_id → {dim_alias}.region_id")

    if 'fact_order.province' in sql.lower():
        sql = sql.replace('fact_order.province', f'{fact_alias}.region_id')
        logger.info(f"✅ 自动修正: fact_order.province → {fact_alias}.region_id")

    # ✅ 额外检测：ON fact_order.province = dim_region.province（无别名）
    if 'fact_order.province' in sql.lower() and 'dim_region.province' in sql.lower():
        sql = sql.replace('fact_order.province = dim_region.province',
                          f'{fact_alias}.region_id = {dim_alias}.region_id')
        logger.info(
            f"✅ 自动修正: fact_order.province = dim_region.province → {fact_alias}.region_id = {dim_alias}.region_id")

    # ✅ 检测 ON fact_order.region_id = dim_region.region_id 但用了别名
    if 'fact_order.region_id' in sql.lower() and fact_alias != 'fact_order':
        sql = sql.replace('fact_order.region_id', f'{fact_alias}.region_id')
    if 'dim_region.region_id' in sql.lower() and dim_alias != 'dim_region':
        sql = sql.replace('dim_region.region_id', f'{dim_alias}.region_id')

    if original_sql != sql:
        logger.info(f"📝 修正后 SQL: {sql[:200]}...")

    return sql

async def correct_sql(state: DataAgentState, runtime: Runtime[DataAgentContext]):
    """
    校正 SQL 节点

    当 validate_sql 发现 SQL 错误时，调用 LLM 根据错误信息修正 SQL
    """
    step = "校正SQL"
    writer = runtime.stream_writer

    writer({"type": "progress", "step": step, "status": "running"})

    try:
        # ✅ 获取状态信息
        query = state.get("query", "")
        sql = state.get("sql", "")
        error = state.get("error", "")
        table_infos = state.get("table_infos", [])
        metric_infos = state.get("metric_infos", [])
        date_info = state.get("date_info", {})
        db_info = state.get("db_info", {})

        logger.info(f"原始SQL: {sql}")
        logger.info(f"错误信息: {error}")

        # ✅ ===== 先尝试规则修正（不调 LLM） =====
        fixed_sql = fix_wrong_join(sql)

        # ✅ 如果规则修正成功，验证一下
        if fixed_sql != sql:
            # 用 sql_validator 快速验证
            try:
                is_valid, result = await sql_validator.validate(fixed_sql, state.get("user_info", {}))
                if is_valid:
                    logger.info(f"✅ 规则修正成功，跳过 LLM 校正")
                    writer({"type": "progress", "step": step, "status": "success"})
                    return {"sql": fixed_sql, "error": ""}
            except:
                pass

        # ✅ 如果规则修正失败，使用 LLM 修正
        logger.info("⚠️ 规则修正失败，使用 LLM 校正")

        # ✅ 构建提示词
        prompt = PromptTemplate(
            template=load_prompt("correct_sql"),
            input_variables=["query", "sql", "error", "table_infos", "metric_infos", "date_info", "db_info"],
        )

        output_parser = StrOutputParser()
        chain = prompt | llm | output_parser

        result = await chain.ainvoke({
            "query": query,
            "sql": sql,
            "error": error,
            "table_infos": table_infos,
            "metric_infos": metric_infos,
            "date_info": date_info,
            "db_info": db_info,
        })

        corrected_sql = result.strip()
        corrected_sql = re.sub(r'^```sql\s*', '', corrected_sql)
        corrected_sql = re.sub(r'\s*```$', '', corrected_sql)
        corrected_sql = corrected_sql.strip()

        # ✅ 再用规则修正一次（确保 LLM 结果正确）
        corrected_sql = fix_wrong_join(corrected_sql)

        # ✅ 安全检查
        if not is_safe_sql(corrected_sql):
            logger.error(f"❌ 校正后的 SQL 包含危险操作: {corrected_sql}")
            writer({"type": "error", "message": "生成的 SQL 包含危险操作，已被拦截"})
            return {"sql": "", "error": "危险 SQL 被拦截"}

        logger.info(f"校正后的SQL：{corrected_sql}")
        writer({"type": "progress", "step": step, "status": "success"})
        return {"sql": corrected_sql, "error": ""}

    except Exception as e:
        logger.error(f"{step} failed: {e}")
        writer({"type": "progress", "step": step, "status": "error"})
        return {"sql": "", "error": str(e)}