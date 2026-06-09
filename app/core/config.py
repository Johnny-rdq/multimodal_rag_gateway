"""配置管理 — 从 .env 文件加载环境变量，通过 settings 单例供全局使用"""
import os
from dotenv import load_dotenv

load_dotenv()  # 加载项目根目录 .env 文件


class Settings:
    """应用配置类 — 集中管理所有环境变量"""
    DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY")  # 阿里云 DashScope API 密钥（必填）
    DEFAULT_MODEL = os.getenv("LLM_MODEL", "qwen-vl-plus")  # 视觉理解模型，用于图片描述
    OCR_LANG = os.getenv("OCR_LANG", "ch")  # PaddleOCR 识别语言
    TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")


settings = Settings()  # 全局配置单例
