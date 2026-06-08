"""API 路由 — 聊天 + 会话管理 + 图片上传"""
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
    query: str = ""
    session_id: str = "default"
    image_path: str = ""


@router.post("/chat")
async def chat_endpoint(request: ChatRequest):
    save_message(request.session_id, "user", request.query or "[上传了图片]")
    return StreamingResponse(
        multimodal_generator(request.query, request.image_path, request.session_id),
        media_type="text/event-stream"
    )


@router.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    ext = os.path.splitext(file.filename or "img.jpg")[1]
    filename = f"{uuid.uuid4().hex}{ext}"
    filepath = os.path.join(UPLOAD_DIR, filename)
    with open(filepath, "wb") as f:
        shutil.copyfileobj(file.file, f)
    return {"message": "上传成功", "image_path": filepath, "filename": file.filename}


@router.get("/history")
async def get_history(session_id: str = "default"):
    return {"session_id": session_id, "messages": get_all_messages(session_id)}


@router.get("/sessions")
async def list_sessions():
    return get_all_sessions()


@router.post("/sessions")
async def new_session():
    return create_session()


@router.delete("/sessions/{session_id}")
async def remove_session(session_id: str):
    delete_session(session_id)
    return {"message": "已删除"}
