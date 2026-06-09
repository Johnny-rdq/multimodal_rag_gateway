"""OCR 文字提取 — 使用 PaddleOCR 识别图片中的文字（可选功能）
- PaddleOCR 仅支持 Python 3.12 及以下，3.13+ 会导入失败
- 导入或初始化失败时优雅降级，extract_text() 返回空字符串
- 系统会回退到仅靠 Qwen-VL 视觉描述来理解图片
"""
import logging
logger = logging.getLogger(__name__)

_ocr = None  # PaddleOCR 实例（懒加载）
_ocr_available = True  # OCR 功能是否可用


def _init_ocr():
    """懒加载初始化 PaddleOCR（首次调用时才加载，节省启动时间）"""
    global _ocr, _ocr_available
    if _ocr is not None:
        return
    try:
        from paddleocr import PaddleOCR
        _ocr = PaddleOCR(lang="ch", use_angle_cls=True)
    except ImportError:
        _ocr_available = False
        logger.warning("PaddleOCR 未安装，OCR 功能不可用。pip install paddleocr paddlepaddle")
    except Exception as e:
        _ocr_available = False
        logger.warning(f"PaddleOCR 初始化失败: {e}")


def extract_text(image_path: str) -> str:
    """从图片中提取文字，只返回置信度 > 0.5 的行，失败时返回空字符串"""
    _init_ocr()
    if not _ocr_available or _ocr is None:
        return ""
    try:
        result = _ocr.ocr(image_path, cls=True)
        lines = []
        if result and result[0]:
            for line in result[0]:
                text = line[1][0]
                if line[1][1] > 0.5:  # 仅保留识别置信度高于 0.5 的结果
                    lines.append(text)
        return "\n".join(lines) if lines else ""
    except Exception:
        return ""
