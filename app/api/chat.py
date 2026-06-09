"""API 路由 — 聊天 + 图片上传 + 会话管理
端点：
- POST /api/chat     — SSE 流式聊天（支持图片 + 文本）
- POST /api/upload   — 图片上传
- GET  /api/history  — 获取会话聊天历史
- GET  /api/sessions — 获取所有会话列表
- POST /api/sessions — 创建新会话
- DELETE /api/sessions/{id} — 删除会话
"""
import os
import uuid
import shutil
from fastapi import APIRouter, UploadFile, File
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel

from app.services.multimodal_service import multimodal_generator
from app.database.sqlite_store import (
    save_message, get_all_messages, create_session,
    get_all_sessions, delete_session
)

router = APIRouter()
UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "uploads")


class ChatRequest(BaseModel):
    """聊天请求体模型"""
    query: str = ""           # 用户文本问题（可选，纯图片时为空）
    session_id: str = "default"  # 会话 ID
    image_path: str = ""      # 已上传图片的本地路径


@router.post("/chat")
async def chat_endpoint(request: ChatRequest):
    """SSE 流式聊天 — 先保存用户消息，再通过 StreamingResponse 流式返回 AI 回答"""
    save_message(request.session_id, "user", request.query or "[上传了图片]")
    return StreamingResponse(
        multimodal_generator(request.query, request.image_path, request.session_id),
        media_type="text/event-stream"
    )


@router.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    """图片上传 — 用 UUID 生成唯一文件名，保存到 uploads/ 目录"""
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    ext = os.path.splitext(file.filename or "img.jpg")[1]  # 提取扩展名
    filename = f"{uuid.uuid4().hex}{ext}"  # UUID 防文件名冲突
    filepath = os.path.join(UPLOAD_DIR, filename)
    with open(filepath, "wb") as f:
        shutil.copyfileobj(file.file, f)  # 高效流式复制文件
    return {"message": "上传成功", "image_path": filepath, "filename": file.filename}


@router.get("/history")
async def get_history(session_id: str = "default"):
    """获取指定会话的完整聊天历史"""
    return {"session_id": session_id, "messages": get_all_messages(session_id)}


@router.get("/sessions")
async def list_sessions():
    """获取所有会话列表（按最后活跃时间降序）"""
    return get_all_sessions()


@router.post("/sessions")
async def new_session():
    """创建新会话，返回会话 ID 和标题"""
    return create_session()


@router.delete("/sessions/{session_id}")
async def remove_session(session_id: str):
    """删除指定会话及其所有消息"""
    delete_session(session_id)
    return {"message": "已删除"}
