import logging
import sys
from pathlib import Path

from loguru import logger

from app.conf.app_config import app_config


def setup_logging():
    """配置日志系统"""

    # 移除默认的 handler
    logger.remove()

    # 配置控制台日志
    if app_config.logging.console.enable:
        logger.add(
            sys.stdout,
            level=app_config.logging.console.level,
            format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
            colorize=True,
        )

    # 配置文件日志
    if app_config.logging.file.enable:
        log_path = Path(app_config.logging.file.path)
        log_path.mkdir(parents=True, exist_ok=True)

        logger.add(
            log_path / "app_{time:YYYY-MM-DD}.log",
            level=app_config.logging.file.level,
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
            rotation=app_config.logging.file.rotation,
            retention=app_config.logging.file.retention,
            compression="zip",
        )

    return logger


# 创建全局 logger 实例
logger = setup_logging()

if __name__ == '__main__':
    # 测试日志
    logger.info("日志系统初始化成功！")
    logger.debug("这是一条调试日志")
    logger.warning("这是一条警告日志")