import yaml
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import PromptTemplate
from langgraph.runtime import Runtime

from app.agent.context import DataAgentContext
from app.agent.llm import llm
from app.agent.state import DataAgentState, TableInfoState
from app.core.log import logger
from app.prompt.prompt_loader import load_prompt


async def filter_table(state: DataAgentState, runtime: Runtime[DataAgentContext]):
    step = "过滤表信息"
    writer = runtime.stream_writer

    writer({"type": "progress", "step": step, "status": "running"})

    try:
        query = state.get("query", "")
        table_infos: list[TableInfoState] = state.get("table_infos", [])

        # ✅ 如果没有表信息，直接返回
        if not table_infos:
            logger.warning("table_infos 为空，跳过过滤")
            writer({"type": "progress", "step": step, "status": "success"})
            return {"table_infos": []}

        # ✅ 限制传递给 LLM 的数据量，避免 token 超限
        limited_table_infos = table_infos[:20]  # 最多处理 20 个表

        prompt = PromptTemplate(
            template=load_prompt("filter_table_info"),
            input_variables=["query", "table_infos"],
        )
        output_parser = JsonOutputParser()
        chain = prompt | llm | output_parser

        result = await chain.ainvoke(
            {
                "query": query,
                "table_infos": yaml.dump(
                    limited_table_infos,
                    allow_unicode=True,
                    sort_keys=False,
                    default_flow_style=False
                ),
            }
        )

        # ✅ 处理 LLM 返回结果
        filtered_table_infos: list[TableInfoState] = []
        if result and isinstance(result, dict):
            for table_info in limited_table_infos:
                table_name = table_info.get("name", "")
                if table_name in result:
                    selected_columns = result.get(table_name, [])
                    if selected_columns:
                        # 过滤列
                        table_info["columns"] = [
                            column_info
                            for column_info in table_info.get("columns", [])
                            if column_info.get("name") in selected_columns
                        ]
                        filtered_table_infos.append(table_info)
                    else:
                        # 如果表被选中但没有列，保留表但清空列
                        table_info["columns"] = []
                        filtered_table_infos.append(table_info)

        # ✅ 关键修复：如果 LLM 没有返回任何表，保留所有原始表
        if not filtered_table_infos:
            logger.warning("LLM 没有返回任何表，保留所有原始表以避免 SQL 生成失败")
            # 保留原始表，但清空列信息（让后续节点重新填充）
            for table_info in table_infos:
                table_info["columns"] = []
            filtered_table_infos = table_infos

        logger.info(f"过滤后的表信息：{[t.get('name', '') for t in filtered_table_infos]}")

        writer({"type": "progress", "step": step, "status": "success"})
        return {"table_infos": filtered_table_infos}

    except yaml.YAMLError as e:
        logger.error(f"{step} YAML 序列化失败: {e}")
        writer({"type": "progress", "step": step, "status": "error"})
        # ✅ 发生错误时返回原始表，避免流程中断
        return {"table_infos": state.get("table_infos", [])}
    except Exception as e:
        logger.error(f"{step} failed: {e}")
        writer({"type": "progress", "step": step, "status": "error"})
        # ✅ 发生错误时返回原始表，避免流程中断
        return {"table_infos": state.get("table_infos", [])}