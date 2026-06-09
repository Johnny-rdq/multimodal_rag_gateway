# app/core/pdf_processor.py
import os
import uuid
import pdfplumber
import logging
from app.processors.vision import describe_image_for_embedding

# 设置日志，方便我们在终端排查报错
logger = logging.getLogger(__name__)


def process_pdf(pdf_path: str, upload_dir: str) -> list[str]:
    """
    解析 PDF：提取每页文字，并将图表裁剪出来交由视觉大模型分析。
    返回按页划分的富文本区块列表。
    """
    chunks = []

    try:
        with pdfplumber.open(pdf_path) as pdf:
            for i, page in enumerate(pdf.pages):
                # 1. 提取纯文本
                page_text = page.extract_text() or ""
                page_content = f"【第{i + 1}页文本内容】\n{page_text}\n"

                # 2. 查找并提取页面中的图片/图表
                for img_idx, img in enumerate(page.images):
                    try:
                        # 获取图片边界框并裁剪
                        bbox = (img["x0"], img["top"], img["x1"], img["bottom"])
                        cropped_page = page.crop(bbox)
                        img_obj = cropped_page.to_image(resolution=150)

                        # 生成临时图片
                        temp_img_path = os.path.join(upload_dir, f"temp_chart_{uuid.uuid4().hex}.png")
                        img_obj.save(temp_img_path, format="PNG")

                        # 调用视觉模型
                        chart_desc = describe_image_for_embedding(temp_img_path)
                        page_content += f"\n【第{i + 1}页 - 图表{img_idx + 1}描述】\n{chart_desc}\n"

                        # 清理临时文件
                        if os.path.exists(temp_img_path):
                            os.remove(temp_img_path)

                    except Exception as e:
                        # 局部报错，不影响整个文件的解析
                        logger.warning(f"第{i + 1}页图表提取失败: {e}")
                        continue

                if page_content.strip():
                    chunks.append(page_content)

    except Exception as e:
        logger.error(f"PDF 解析整体失败: {e}")

    return chunks