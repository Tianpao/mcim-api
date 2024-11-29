
from loguru import logger
import os
import sys
import re
import logging
import time

from app.config import MCIMConfig

if os.getenv("TZ") is not None:
    time.tzset()

mcim_config = MCIMConfig.load()

# 清空 root 日志器的 handlers
logging.root.handlers = []

# 定义一个拦截标准日志的处理器
class InterceptHandler(logging.Handler):
    def emit(self, record):
        # 获取对应的 Loguru 日志等级
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno
        # 重建 LogRecord，以确保格式正确
        frame, depth = logging.currentframe(), 2
        while frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1
        logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())

# 配置 Loguru 日志器
logger.remove()
logger.add(
    sys.stdout,
    level="DEBUG" if mcim_config.debug else "INFO",
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{module}</cyan>.<cyan>{function}</cyan>.<cyan>{line}</cyan> | <cyan>{message}</cyan>",
    colorize=True,
    backtrace=True,
    diagnose=True,
)

# 拦截标准日志并重定向到 Loguru
logging.basicConfig(handlers=[InterceptHandler()], level=0)

# 要忽略的路由列表
routes_to_ignore = [r"/metrics", r"^/data/.*", r"^/files/.*"]

# 定义过滤器
def filter_uvicorn_access(record: logging.LogRecord) -> bool:
    message = record.getMessage()
    # 使用正则表达式提取请求路径
    match = re.search(r'"[A-Z]+ (.+?) HTTP/.*"', message)
    if match:
        path = match.group(1)
        for route_pattern in routes_to_ignore:
            if re.match(route_pattern, path):
                return False  # 过滤该日志
    return True  # 保留该日志

# 为 uvicorn.access 日志器添加过滤器
access_logger = logging.getLogger("uvicorn.access")
access_logger.addFilter(filter_uvicorn_access)

# 处理 uvicorn 日志器
for uvicorn_logger in ("uvicorn", "uvicorn.error", "uvicorn.access", "uvicorn.asgi"):
    uv_logger = logging.getLogger(uvicorn_logger)
    uv_logger.handlers = [InterceptHandler()]
    uv_logger.propagate = False

# 禁用日志器
logging.getLogger("httpx").propagate = False
logging.getLogger("httpcore").propagate = False
logging.getLogger("pymongo").propagate = False

# 导出 logger
log = logger