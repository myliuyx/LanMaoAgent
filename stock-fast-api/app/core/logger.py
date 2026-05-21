"""日志配置"""
import logging
import sys

# 创建一个全局 logger
logger = logging.getLogger("stock_api")
logger.setLevel(logging.INFO)

# 控制台输出格式
handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.INFO)
formatter = logging.Formatter(
    fmt="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
handler.setFormatter(formatter)

# 避免重复添加 handler
if not logger.handlers:
    logger.addHandler(handler)
