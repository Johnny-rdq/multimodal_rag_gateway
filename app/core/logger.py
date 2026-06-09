# app/core/logger.py
import logging
import sys
import os
from logging.handlers import RotatingFileHandler

def setup_logger(name="NexusAI"):
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    if not logger.handlers:
        # 定义高颜值的统一格式
        formatter = logging.Formatter(
            fmt="%(asctime)s | %(levelname)-8s | %(module)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )

        # === 1. 终端处理器 (打印在屏幕上，供开发时实时观看) ===
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

        # === 2. 文件处理器 (自动存入本地黑匣子，供线上排查 Bug) ===
        # 自动计算项目根目录，并创建 logs 文件夹
        BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        log_dir = os.path.join(BASE_DIR, "logs")
        os.makedirs(log_dir, exist_ok=True)
        log_file = os.path.join(log_dir, "nexus_ai.log")

        # 【核心黑科技】：RotatingFileHandler (滚动日志)
        # 限制每个日志文件最大 5MB (maxBytes=5*1024*1024)
        # 最多保留 3 个旧备份 (backupCount=3)
        # 当文件超过 5MB 时，它会自动重命名为 nexus_ai.log.1，并创建一个新的空白日志继续写，绝不会撑爆硬盘！
        file_handler = RotatingFileHandler(
            filename=log_file,
            maxBytes=5 * 1024 * 1024,
            backupCount=3,
            encoding="utf-8"
        )
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger

logger = setup_logger()