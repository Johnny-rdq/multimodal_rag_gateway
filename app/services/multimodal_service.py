"""多模态 RAG 核心服务"""
import os
import asyncio
import dashscope

from app.core.config import settings
from app.database.chroma_store import add_to_db, query_db
from app.database.sqlite_store import save_message, get_recent_messages

from app.processors.vision import analyze_image, describe_image_for_embedding
from app.processors.ocr import extract_text
from app.processors.pdf_processor import process_pdf
from app.processors.text_processor import process_txt, process_docx

from app.agents.agent_router import determine_route
from app.agents.tools.search_tool import search_web

from app.core.logger import logger

dashscope.api_key = settings.DASHSCOPE_API_KEY
UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "uploads")

def ingest_document(file_path: str) -> str:
    """【核心修复 1】自动判断文件类型，并强制提取前 300 字预览，防大模型变瞎"""
    ext = os.path.splitext(file_path)[1].lower()

    if ext == '.pdf':
        chunks = process_pdf(file_path, UPLOAD_DIR)
        if chunks:
            metadatas = [{"file_path": file_path, "page": i + 1} for i in range(len(chunks))]
            add_to_db(chunks, metadatas)
            preview = "\n".join(chunks[:2])[:300] # 强行截取开头内容
            return f"【系统信息】已加载PDF文件。\n【文档开头预览】:\n{preview}..."
        return "PDF解析失败或文件为空。"

    elif ext == '.txt':
        chunks = process_txt(file_path)
        if chunks:
            metadatas = [{"file_path": file_path} for _ in range(len(chunks))]
            add_to_db(chunks, metadatas)
            preview = "\n".join(chunks[:3])[:300]
            return f"【系统信息】已加载TXT文件。\n【文档开头预览】:\n{preview}..."
        return "TXT解析失败或文件为空。"

    elif ext == '.docx':
        chunks = process_docx(file_path)
        if chunks:
            metadatas = [{"file_path": file_path} for _ in range(len(chunks))]
            add_to_db(chunks, metadatas)
            preview = "\n".join(chunks[:3])[:300]
            return f"【系统信息】已加载Word文件。\n【文档开头预览】:\n{preview}..."
        return "Word文档解析失败或文件为空。"

    elif ext in ['.jpg', '.jpeg', '.png']:
        return ingest_image(file_path)
    else:
        return f"系统暂不支持解析 {ext} 格式"

def process_image(image_path: str) -> dict:
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    ocr_text = extract_text(image_path)
    vision_desc = describe_image_for_embedding(image_path)
    combined = f"[视觉描述] {vision_desc}"
    if ocr_text:
        combined += f"\n[OCR文字] {ocr_text}"
    return {"description": combined, "ocr_text": ocr_text, "vision_desc": vision_desc}

def ingest_image(image_path: str) -> str:
    result = process_image(image_path)
    chunks = [c.strip() for c in result["description"].split("\n") if c.strip()]
    metadatas = [{"image_path": image_path} for _ in chunks]
    add_to_db(chunks, metadatas)
    return result["description"]

async def multimodal_generator(query: str, session_id: str, image_path: str = None):
    display_query = query if query.strip() else "[附件文档分析]"
    save_message(
        session_id=session_id,
        role="user",
        content=display_query,
        context="",
        image_path=image_path if image_path else ""
    )

    final_text = ""
    context_text = ""
    current_file_desc = ""

    try:
        yield "data: [STATUS]: 大脑正在思考处理方案...\n\n"
        await asyncio.sleep(0)

        route = determine_route(query, bool(image_path and os.path.exists(image_path)))
        logger.info(f"路由大脑决策完成，当前用户问题分配至 ===> [{route.upper()}] 分支")
        yield f"data: [STATUS]: 决策完成，进入 [{route.upper()}] 分支\n\n"
        await asyncio.sleep(0)

        rag_context = ""

        if route == "vision":
            yield "data: [STATUS]: 正在深度解析文件内容...\n\n"
            await asyncio.sleep(0)

            current_file_desc = ingest_document(image_path)

            # 默认来源显示为文档开头的提取预览
            context_text = current_file_desc.replace("\n", " ")[:150] + "..."

            ext = os.path.splitext(image_path)[1].lower() if image_path else ""
            if ext in ['.pdf', '.txt', '.docx']:
                search_query = query
                if len(query.strip()) <= 4:
                    search_query = "摘要 总结 核心内容 简介"

                retrieved = query_db(search_query, n_results=4, where_filter={"file_path": image_path})
                if retrieved:
                    rag_context = "\n\n【文档相关片段提取】\n" + "\n".join(retrieved)
                    # 👇 核心修复 1：将真实检索回来的段落截断作为来源展示！
                    pure_text = " ".join(retrieved).replace("\n", " ")
                    context_text = pure_text[:150] + "..." if len(pure_text) > 150 else pure_text

        elif route == "rag":
            yield "data: [STATUS]: 正在检索历史知识库...\n\n"
            await asyncio.sleep(0)
            retrieved = query_db(query, n_results=3) if query.strip() else []
            if retrieved:
                rag_context = "\n\n【相关知识】\n" + "\n".join(retrieved)
                # 👇 核心修复 2：真实的历史知识片段
                pure_text = " ".join(retrieved).replace("\n", " ")
                context_text = pure_text[:150] + "..." if len(pure_text) > 150 else pure_text

        elif route == "search":
            yield "data: [STATUS]: 正在联网获取最新资讯...\n\n"
            await asyncio.sleep(0)
            search_result = search_web(query)
            logger.info(f"成功触发全网搜索，截取上下文长度: {len(search_result)} 字符")
            if search_result and len(search_result) > 50:
                rag_context = "\n\n【全网实时搜索结果】\n" + search_result
                # 👇 核心修复 3：真实的联网搜索片段
                pure_text = search_result.replace("\n", " ")
                context_text = pure_text[:150] + "..." if len(pure_text) > 150 else pure_text
            else:
                context_text = "联网搜索未找到相关结果"

        system_prompt = "你是多模态AI助理。请根据提供的解析内容或知识库准确回答，不知道就说不知道，不要编造。"
        messages = [{"role": "system", "content": system_prompt}]

        history = get_recent_messages(session_id, limit=6)
        for h in history:
            if h["content"] != display_query:
                messages.append({"role": h["role"], "content": h["content"]})

        user_content = ""
        if current_file_desc:
            user_content += f"{current_file_desc}\n\n"
        if rag_context:
            user_content += f"{rag_context}\n\n"
        user_content += f"【用户问题】{query}"

        messages.append({"role": "user", "content": user_content})

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
            final_text = f"调用失败: {response.message}"
            yield f"data: {final_text}\n\n"

        if context_text:
            yield f"data: [SOURCE]: {context_text}\n\n"

    except Exception as e:
        final_text = f"服务出错: {str(e)}"
        yield f"data: {final_text}\n\n"

    if final_text and "服务出错" not in final_text:
        save_message(
            session_id=session_id,
            role="assistant",
            content=final_text,
            context=context_text,
            image_path=""
        )