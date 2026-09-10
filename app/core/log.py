from loguru import logger

from app.core.context import request_id_ctx_var

# 日志格式统一展示时间、级别、request_id 和调用位置，便于排查链路问题
log_format = (
    "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
    "<level>{level: <8}</level> | "
    "<magenta>request_id - {extra[request_id]}</magenta> | "
    "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
    "<level>{message}</level>"
)


def inject_request_id(record):
    """把上下文中的 request_id 注入到每条日志的 extra 字段"""
    request_id = request_id_ctx_var.get()
    record["extra"]["request_id"] = request_id


# 移除 Loguru 默认的输出目标，避免和项目自定义配置重复打印
logger.remove()

# 配置日志格式
logger.add(
    sink=lambda msg: print(msg, end=""),
    format=log_format,
    colorize=True,
)

# 生成带 request_id 注入能力的 logger，后续业务代码统一使用这个实例
logger = logger.patch(inject_request_id)