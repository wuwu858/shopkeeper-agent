import yaml
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import PromptTemplate
from langgraph.runtime import Runtime

from app.agent.context import DataAgentContext
from app.agent.llm import llm
from app.agent.state import DataAgentState, MetricInfoState
from app.core.log import logger
from app.prompt.prompt_loader import load_prompt


async def filter_metric(state: DataAgentState, runtime: Runtime[DataAgentContext]):
    step = "过滤指标信息"
    writer = runtime.stream_writer

    writer({"type": "progress", "step": step, "status": "running"})

    try:
        query = state.get("query", "")
        metric_infos: list[MetricInfoState] = state.get("metric_infos", [])

        # ✅ 如果没有指标信息，直接返回
        if not metric_infos:
            logger.warning("metric_infos 为空，跳过过滤")
            writer({"type": "progress", "step": step, "status": "success"})
            return {"metric_infos": []}

        # ✅ 限制传递给 LLM 的数据量
        limited_metric_infos = metric_infos[:20]  # 最多处理 20 个指标

        prompt = PromptTemplate(
            template=load_prompt("filter_metric_info"),
            input_variables=["query", "metric_infos"],
        )
        output_parser = JsonOutputParser()
        chain = prompt | llm | output_parser

        result = await chain.ainvoke(
            {
                "query": query,
                "metric_infos": yaml.dump(
                    limited_metric_infos,
                    allow_unicode=True,
                    sort_keys=False,
                    default_flow_style=False
                ),
            }
        )

        # ✅ 处理 LLM 返回结果
        filtered_metric_infos = []
        if result and isinstance(result, list):
            # 如果 LLM 返回的是列表
            selected_names = set(result)
            filtered_metric_infos = [
                metric_info
                for metric_info in limited_metric_infos
                if metric_info.get("name") in selected_names
            ]
        elif result and isinstance(result, dict):
            # 如果 LLM 返回的是字典（兼容不同格式）
            selected_names = set(result.keys())
            filtered_metric_infos = [
                metric_info
                for metric_info in limited_metric_infos
                if metric_info.get("name") in selected_names
            ]

        # ✅ 关键修复：如果 LLM 没有返回任何指标，保留所有原始指标
        if not filtered_metric_infos:
            logger.warning("LLM 没有返回任何指标，保留所有原始指标以避免 SQL 生成失败")
            filtered_metric_infos = metric_infos

        logger.info(f"过滤后的指标信息：{[m.get('name', '') for m in filtered_metric_infos]}")

        writer({"type": "progress", "step": step, "status": "success"})
        return {"metric_infos": filtered_metric_infos}

    except yaml.YAMLError as e:
        logger.error(f"{step} YAML 序列化失败: {e}")
        writer({"type": "progress", "step": step, "status": "error"})
        # ✅ 发生错误时返回原始指标
        return {"metric_infos": state.get("metric_infos", [])}
    except Exception as e:
        logger.error(f"{step} failed: {e}")
        writer({"type": "progress", "step": step, "status": "error"})
        # ✅ 发生错误时返回原始指标
        return {"metric_infos": state.get("metric_infos", [])}