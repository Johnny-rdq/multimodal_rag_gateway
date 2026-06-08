"""多模态 RAG 核心服务 — 图片分析 + 检索 + LLM 回答"""
import os
import json
import asyncio
import dashscope
import uuid
from app.core.config import settings
from app.core.vision import analyze_image, describe_image_for_embedding
from app.core.ocr import extract_text
from app.database.chroma_store import add_to_db, query_db, get_all_docs
from app.database.sqlite_store import save_message, get_recent_messages

dashscope.api_key = settings.DASHSCOPE_API_KEY

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "uploads")


def process_image(image_path: str) -> dict:
    """处理单张图片：OCR 提取 + 视觉理解 → 返回文本描述"""
    os.makedirs(UPLOAD_DIR, exist_ok=True)

    # OCR 文字提取
    ocr_text = extract_text(image_path)
    # 视觉理解
    vision_desc = describe_image_for_embedding(image_path)

    combined = f"[视觉描述] {vision_desc}"
    if ocr_text:
        combined += f"\n[OCR文字] {ocr_text}"

    return {"description": combined, "ocr_text": ocr_text, "vision_desc": vision_desc}


def ingest_image(image_path: str) -> str:
    """图片入库：分析 → 向量化存储"""
    result = process_image(image_path)
    # 按段落分块
    chunks = [c.strip() for c in result["description"].split("\n") if c.strip()]
    metadatas = [{"image_path": image_path} for _ in chunks]
    add_to_db(chunks, metadatas)
    return result["description"]


async def multimodal_generator(query: str, image_path: str, session_id: str):
    """多模态 RAG 生成器 — SSE 流式输出"""
    final_text = ""
    context_text = ""

    try:
        # 1. 有图片先分析
        if image_path and os.path.exists(image_path):
            yield "data: [STATUS]: 正在分析图片...\n\n"
            await asyncio.sleep(0)

            image_desc = ingest_image(image_path)
            context_text = image_desc[:200] + "..." if len(image_desc) > 200 else image_desc

        # 2. 向量检索
        retrieved = query_db(query, n_results=3) if query.strip() else []

        # 3. 构建消息
        rag_context = ""
        if retrieved:
            rag_context = "\n\n【相关知识】\n" + "\n".join(retrieved)

        system_prompt = "你是多模态AI助理。优先参考【相关知识】回答用户问题。回答简洁准确，用中文。"

        messages = [{"role": "system", "content": system_prompt}]
        history = get_recent_messages(session_id, limit=6)
        for h in history:
            messages.append({"role": h["role"], "content": h["content"]})

        user_content = f"{rag_context}\n\n【用户问题】{query}" if rag_context else query
        messages.append({"role": "user", "content": user_content})

        # 4. 调用 LLM
        yield "data: [THINKING]: 正在回答...\n\n"
        await asyncio.sleep(0)

        response = await asyncio.to_thread(
            dashscope.Generation.call,
            model="qwen-turbo",
            messages=messages,
            result_format="message"
        )

        if response.status_code == 200:
            final_text = response.output.choices[0].message.content or ""
            for i in range(0, len(final_text), 6):
                yield f"data: {final_text[i:i + 6]}\n\n"
                await asyncio.sleep(0.005)
        else:
            yield f"data: 调用失败: {response.message}\n\n"

        # 5. 最后显示来源
        if context_text:
            yield f"data: [SOURCE]: {context_text}\n\n"

    except Exception as e:
        yield f"data: 服务出错: {str(e)}\n\n"
        final_text = f"服务出错: {str(e)}"

    if final_text and "服务出错" not in final_text:
        save_message(session_id, "assistant", final_text, context_text, image_path or "")
