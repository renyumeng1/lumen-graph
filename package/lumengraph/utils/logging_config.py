"""日志配置模块。

提供基于 Loguru 的统一日志配置，包括：
- 文件日志：按日期分割、自动压缩、超大自动轮转
- 控制台日志：彩色输出、格式化显示
- 日志桥接：将第三方库（httpx、openai、neo4j、urllib3）的标准 logging 桥接到 Loguru

Example:
    >>> from lumengraph.utils.logging_config import logger
    >>> logger.info("Hello world")
    >>> logger.debug("Debug message")
    >>> logger.error("Error occurred", exc_info=True)
"""

import logging
import os
import sys


from loguru import logger as loguru_logger
from lumengraph.utils.datetime_utils import shanghai_now

SAVE_DIR = "saves"
DATETIME = shanghai_now().strftime("%Y-%m-%d")
LOG_FILE = f"{SAVE_DIR}/logs/lumengraph-{DATETIME}.log"


class LoguruHandler(logging.Handler):
    """将标准 logging 日志桥接到 Loguru 的 Handler。

    通过实现 logging.Handler 接口，将标准 logging 模块的日志记录
    转发到 Loguru，实现统一的日志输出格式。

    Example:
        >>> import logging
        >>> handler = LoguruHandler()
        >>> handler.setFormatter(logging.Formatter("%(message)s"))
        >>> root_logger = logging.getLogger()
        >>> root_logger.addHandler(handler)
    """

    def emit(self, record: logging.LogRecord) -> None:
        """将一条日志记录转发到 Loguru。

        Args:
            record: logging 模块的 LogRecord 对象。
        """
        level_map = {
            logging.DEBUG: "DEBUG",
            logging.INFO: "INFO",
            logging.WARNING: "WARNING",
            logging.ERROR: "ERROR",
            logging.CRITICAL: "CRITICAL",
        }
        level = level_map.get(record.levelno, "DEBUG")
        try:
            msg = self.format(record)
        except Exception:
            msg = record.getMessage()
        loguru_logger.opt(depth=1, exception=record.exc_info).log(level, msg)


def _setup_logging_bridge() -> None:
    """为第三方库设置 logging 到 Loguru 的桥接。

    将 httpx、openai、neo4j、urllib3 等库的标准 logging 输出
    桥接到 Loguru，避免日志分散在多个处理器。

    Note:
        此函数在模块导入时自动调用，用于初始化日志桥接。
    """
    loguru_handler = LoguruHandler()
    loguru_handler.setLevel(logging.DEBUG)

    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    loguru_handler.setFormatter(formatter)

    for lib in ["httpx", "openai", "neo4j", "urllib3"]:
        lib_logger = logging.getLogger(lib)
        lib_logger.addHandler(loguru_handler)
        lib_logger.setLevel(logging.WARNING)
        lib_logger.propagate = False


def setup_logger(name: str, level: str = "DEBUG", console: bool = True) -> loguru_logger:
    """配置并返回 Loguru logger 实例。

    设置文件日志和控制台日志输出：
    - 文件日志：保存到 saves/logs/，自动按日期命名，10MB 轮转，保留 30 天
    - 控制台日志：彩色输出，带时间戳和代码位置信息

    Args:
        name: logger 名称（用于标识日志来源）。
        level: 日志级别，默认为 "DEBUG"。
        console: 是否启用控制台输出，默认为 True。

    Returns:
        配置好的 Loguru logger 实例。

    Example:
        >>> my_logger = setup_logger("MyModule", level="INFO")
        >>> my_logger.info("This will be logged")
    """
    os.makedirs(f"{SAVE_DIR}/logs", exist_ok=True)

    loguru_logger.remove()

    loguru_logger.add(
        LOG_FILE,
        level=level,
        format="{time:YYYY-MM-DD HH:mm:ss} - {level} -{file}:{line} - {message}",
        encoding="utf-8",
        rotation="10 MB",
        retention="30 days",
        compression="zip",
        enqueue=True,
    )

    if console:
        loguru_logger.add(
            sys.stderr,
            level=level,
            format=(
                "<green>{time:MM-DD HH:mm:ss}</green> "
                "<level>{level}</level> "
                "<cyan>{file}:{line}</cyan>: "
                "<level>{message}</level>"
            ),
            colorize=True,
            enqueue=True,
        )

    return loguru_logger


logger = setup_logger("Lumengraph")
_setup_logging_bridge()


__all__ = ["logger"]