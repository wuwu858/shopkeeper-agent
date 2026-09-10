# app/agent/nodes/compress_context.py（更新版）

from typing import Dict, List
from langgraph.runtime import Runtime

from app.agent.state import DataAgentState
from app.core.log import logger


async def compress_context(
    state: DataAgentState,
    runtime: Runtime,
) -> Dict:
    """
    压缩对话历史，生成上下文摘要

    策略：
    1. 如果没有历史 → 返回空
    2. 如果历史少于 3 条 → 直接拼接
    3. 如果历史较多 → 用 LLM 压缩
    """
    step = "压缩上下文"
    writer = runtime.stream_writer
    writer({"type": "progress", "step": step, "status": "running"})

    try:
        history = state.get("history", [])
        query = state.get("query", "")

        # 如果没有历史，直接返回
        if not history:
            logger.info("无对话历史，跳过压缩")
            writer({"type": "progress", "step": step, "status": "success"})
            return {"compressed_context": ""}

        # 如果历史少于 3 条，直接拼接
        if len(history) <= 3:
            context = _format_recent_history(history)
            logger.info(f"✅ 直接拼接 {len(history)} 条历史消息")
            logger.info(f"📝 压缩后的上下文:\n{context}")
            writer({"type": "progress", "step": step, "status": "success"})
            return {"compressed_context": context}

        # 历史较多，用 LLM 压缩
        context = await _compress_with_llm(history, query)

        logger.info(f"✅ 上下文压缩完成，原始 {len(history)} 条消息压缩为 {len(context)} 字符")
        logger.info(f"📝 压缩后的上下文:\n{context[:200]}...")

        writer({"type": "progress", "step": step, "status": "success"})
        return {"compressed_context": context}

    except Exception as e:
        logger.error(f"{step} 失败: {e}", exc_info=True)
        writer({"type": "progress", "step": step, "status": "error"})
        # 降级：返回最后几条历史
        fallback_context = _format_recent_history(history[-2:]) if history else ""
        return {"compressed_context": fallback_context}


def _format_recent_history(history: List[Dict]) -> str:
    """
    格式化最近的历史消息
    ✅ 过滤错误 SQL，截断过长 SQL
    """
    lines = []
    for msg in history:
        role = msg.get("role", "")
        content = msg.get("content", "")
        sql = msg.get("sql", "")
        is_success = msg.get("is_success", True)  # ✅ 默认为 True

        if role == "user":
            # 截断过长的用户问题
            if len(content) > 100:
                content = content[:100] + "..."
            lines.append(f"用户问: {content}")

        elif role == "assistant":
            # ✅ 只显示有结果的内容
            if sql and is_success:
                # ✅ 只取 SQL 的关键部分（避免过长）
                sql_preview = sql[:200] + "..." if len(sql) > 200 else sql
                # 截断 content
                if len(content) > 100:
                    content = content[:100] + "..."
                lines.append(f"系统回答: {content} (SQL: {sql_preview})")

            elif sql and not is_success:
                # ✅ 错误 SQL 只记录错误信息，不存 SQL
                lines.append(f"系统回答: {content} (查询失败)")

            else:
                lines.append(f"系统回答: {content}")

    return "\n".join(lines)


async def _compress_with_llm(history: List[Dict], current_query: str) -> str:
    """
    用 LLM 压缩历史消息为摘要
    ✅ 过滤掉错误的 SQL，只保留有效信息
    """
    from app.agent.llm import llm
    from langchain_core.prompts import PromptTemplate
    from langchain_core.output_parsers import StrOutputParser

    # ✅ 格式化历史（最多取 6 条，过滤错误）
    history_text = ""
    valid_count = 0
    for msg in history[-8:]:  # 取最近 8 条，筛选后用
        role = "用户" if msg.get("role") == "user" else "系统"
        content = msg.get("content", "")
        sql = msg.get("sql", "")
        is_success = msg.get("is_success", True)

        # ✅ 只记录成功的 SQL，错误的跳过
        if role == "用户":
            history_text += f"{role}: {content}\n"
            valid_count += 1
        elif role == "系统":
            if sql and is_success:
                # 截断 SQL
                sql_preview = sql[:150] + "..." if len(sql) > 150 else sql
                history_text += f"{role}: {content} (执行的SQL: {sql_preview})\n"
                valid_count += 1
            elif sql and not is_success:
                # ✅ 错误 SQL 只记录失败，不存 SQL
                history_text += f"{role}: {content} (执行失败)\n"
                valid_count += 1
            else:
                history_text += f"{role}: {content}\n"
                valid_count += 1

        # 最多取 6 条有效消息
        if valid_count >= 6:
            break

    # 如果历史为空，返回空
    if not history_text:
        return ""

    prompt = PromptTemplate(
        template="""
你是一个数据分析对话摘要助手。请根据以下对话历史，提取与当前问题相关的关键信息。

## 对话历史
{history}

## 当前问题
{current_query}

## 要求
1. 只提取与当前问题相关的信息
2. 保留关键的实体（表名、字段名、数值、过滤条件）
3. 如果历史中有上次查询的 SQL 或结果，必须提取
4. 如果用户进行了追问，记录追问的上下文关系
5. 输出简洁的摘要，不超过 200 字
6. 如果历史中有错误的 SQL，请忽略它，不要被误导

## 摘要
""",
        input_variables=["history", "current_query"],
    )

    try:
        chain = prompt | llm | StrOutputParser()
        result = await chain.ainvoke({
            "history": history_text,
            "current_query": current_query,
        })
        return result.strip()
    except Exception as e:
        logger.error(f"LLM 压缩失败: {e}")
        # 降级：返回简单拼接
        return _format_recent_history(history[-3:])