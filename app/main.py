# app/main.py
import os
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import uvicorn

from app.services.multimodal_service import multimodal_generator
from app.routers import sessions

app = FastAPI(title="Nexus AI Engine", version="1.0.0")

# 挂载静态目录，让前端可以预览文件
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

app.include_router(sessions.router)

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


class ChatRequest(BaseModel):
    query: str
    session_id: str
    image_path: str = None


@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    try:
        file_ext = os.path.splitext(file.filename)[1].lower()
        # 👇 核心修改：在这里加上 .txt 和 .docx 的白名单
        if file_ext not in [".jpg", ".jpeg", ".png", ".pdf", ".txt", ".docx"]:
            raise HTTPException(status_code=400, detail="不支持的文件格式")

        file_name = f"{os.urandom(8).hex()}{file_ext}"
        file_path = os.path.join(UPLOAD_DIR, file_name)

        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)

        return {"file_path": file_path}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"文件流写入失败: {str(e)}")


@app.post("/api/chat")
async def chat_endpoint(request: ChatRequest):
    try:
        return StreamingResponse(
            multimodal_generator(
                query=request.query,
                image_path=request.image_path,
                session_id=request.session_id
            ),
            media_type="text/event-stream"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"智能体流式响应中断: {str(e)}")


@app.get("/", response_class=HTMLResponse)
async def read_index():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.dirname(current_dir)
    index_path = os.path.join(root_dir, "index.html")

    if os.path.exists(index_path):
        with open(index_path, "r", encoding="utf-8") as f:
            return f.read()
    return f"<h3>找错位置啦！程序当前去这里找了：{index_path}</h3>"


if __name__ == "__main__":
    # 本地开发时 reload=True 会启动两次，上线时去掉即可
    uvicorn.run("app.main:app", host="127.0.0.1", port=8001, reload=True)