# app/agent/nodes/add_extra_context.py

from datetime import datetime
from langgraph.runtime import Runtime

from app.agent.context import DataAgentContext
from app.agent.state import DataAgentState
from app.core.log import logger
from app.core.dictionary_loader import dictionary_loader


async def add_extra_context(state: DataAgentState, runtime: Runtime[DataAgentContext]):
    step = "添加额外上下文"
    writer = runtime.stream_writer

    writer({"type": "progress", "step": step, "status": "running"})

    try:
        # 1. 获取日期信息
        now = datetime.now()
        date_info = {
            "date": now.strftime("%Y-%m-%d"),
            "weekday": now.strftime("%A"),
            "quarter": f"Q{(now.month - 1) // 3 + 1}",
        }

        # 2. 获取数据库信息
        dw_mysql_repository = runtime.context["dw_mysql_repository"]
        db_info = await dw_mysql_repository.get_db_info()

        # 3. ✅ 获取字典信息（修复事务冲突）
        metrics = {}
        dimensions = {}
        region_mapping = {}

        try:
            meta_mysql_repository = runtime.context.get("meta_mysql_repository")
            if meta_mysql_repository:
                # ✅ 直接使用 session，不开启新事务
                # 因为 session 可能已经在事务中
                await dictionary_loader.load_from_db(meta_mysql_repository.session)
                metrics = dictionary_loader.get_metrics()
                dimensions = dictionary_loader.get_dimensions()
                region_mapping = dictionary_loader.get_region_mapping()
                logger.info(f"✅ 字典加载成功: {len(metrics)} 个指标, {len(dimensions)} 个维度")
            else:
                logger.warning("meta_mysql_repository 不存在，跳过字典加载")
        except Exception as e:
            logger.error(f"字典加载失败: {e}")

        # 4. 构建字典上下文
        dictionary_context = {
            "metrics": metrics,
            "dimensions": dimensions,
            "region_mapping": region_mapping
        }

        logger.info(f"日期信息：{date_info}")
        logger.info(f"数据库信息：{db_info}")

        writer({"type": "progress", "step": step, "status": "success"})
        return {
            "date_info": date_info,
            "db_info": db_info,
            "dictionary_context": dictionary_context
        }

    except Exception as e:
        logger.error(f"{step} failed: {e}")
        writer({"type": "progress", "step": step, "status": "error"})
        # 返回默认值，避免整个流程中断
        return {
            "date_info": {},
            "db_info": {},
            "dictionary_context": {}
        }