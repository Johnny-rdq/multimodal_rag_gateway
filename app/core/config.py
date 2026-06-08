import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY")
    DEFAULT_MODEL = os.getenv("LLM_MODEL", "qwen-vl-plus")
    OCR_LANG = os.getenv("OCR_LANG", "ch")


settings = Settings()
