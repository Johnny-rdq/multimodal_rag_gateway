"""OCR 文字提取 — 可选（PaddleOCR 需 Python <= 3.12）"""
import logging
logger = logging.getLogger(__name__)

_ocr = None
_ocr_available = True


def _init_ocr():
    global _ocr, _ocr_available
    if _ocr is not None:
        return
    try:
        from paddleocr import PaddleOCR
        _ocr = PaddleOCR(lang="ch", use_angle_cls=True, show_log=False)
    except ImportError:
        _ocr_available = False
        logger.warning("PaddleOCR 未安装，OCR 功能不可用。pip install paddleocr paddlepaddle")
    except Exception as e:
        _ocr_available = False
        logger.warning(f"PaddleOCR 初始化失败: {e}")


def extract_text(image_path: str) -> str:
    _init_ocr()
    if not _ocr_available or _ocr is None:
        return ""
    try:
        result = _ocr.ocr(image_path, cls=True)
        lines = []
        if result and result[0]:
            for line in result[0]:
                text = line[1][0]
                if line[1][1] > 0.5:
                    lines.append(text)
        return "\n".join(lines) if lines else ""
    except Exception:
        return ""
