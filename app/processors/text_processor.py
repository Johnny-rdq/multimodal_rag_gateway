# app/processors/text_processor.py
import os
from docx import Document

def process_txt(file_path: str) -> list:
    """读取 txt 文件并按空行分块（带中文编码兼容）"""
    try:
        # 优先尝试 utf-8
        with open(file_path, 'r', encoding='utf-8') as f:
            text = f.read()
        return [chunk.strip() for chunk in text.split('\n\n') if chunk.strip()]
    except UnicodeDecodeError:
        # 如果报错，说明可能是 Windows 自带记事本写的 GBK 编码
        with open(file_path, 'r', encoding='gbk') as f:
            text = f.read()
        return [chunk.strip() for chunk in text.split('\n\n') if chunk.strip()]
    except Exception as e:
        print(f"[ERROR] TXT 读取失败: {e}")
        return []

def process_docx(file_path: str) -> list:
    """读取 docx 文件并提取所有段落"""
    try:
        doc = Document(file_path)
        # 提取每一段的文字，过滤掉空行
        return [p.text.strip() for p in doc.paragraphs if p.text.strip()]
    except Exception as e:
        print(f"[ERROR] DOCX 读取失败: {e}")
        return []