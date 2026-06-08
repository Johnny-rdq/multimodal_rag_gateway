"""多模态 RAG 网关 — 入口"""
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from app.api import chat
from app.database.sqlite_store import init_db

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@asynccontextmanager
async def lifespan(app: FastAPI):
    import sys
    init_db()
    sys.stdout.write("[INFO] 多模态 RAG Gateway 启动成功!\n")
    sys.stdout.flush()
    yield


app = FastAPI(title="Multimodal RAG Gateway", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
app.include_router(chat.router, prefix="/api")


@app.get("/")
async def root():
    return FileResponse(os.path.join(ROOT_DIR, "index.html"))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8001)
