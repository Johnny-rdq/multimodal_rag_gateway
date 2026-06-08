# CLAUDE.md

本文件为 Claude Code（claude.ai/code）在此仓库中工作时提供指导。

## 项目概述

基于 FastAPI 的**多模态 RAG 网关**，接收图片上传、通过 OCR + 视觉语言模型提取内容、索引到向量数据库，并结合检索到的上下文通过流式 LLM 对话回答用户问题。前端是单页 HTML 聊天界面（Tailwind CSS + marked.js 渲染 Markdown）。

## 常用命令

```bash
# 启动开发服务器
python -m app.main
# 或：uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload

# 安装依赖
pip install -r requirements.txt
```

项目中未配置测试套件、代码检查或构建步骤。

## 架构

**入口：** `app/main.py` — 创建 FastAPI 应用，注册 CORS 中间件，挂载 `app.api.chat` 的 `/api` 路由，根路径 `/` 返回 `index.html`。运行在 `127.0.0.1:8001`。

**聊天请求处理流水线（`POST /api/chat`）：**
1. 若提供 `image_path`，分析图片：OCR（PaddleOCR）+ 视觉描述（Qwen-VL 通过 DashScope）→ 合并文本分块 → upsert 到 ChromaDB
2. 查询 ChromaDB 获取相关片段（默认 top-3）
3. 用检索到的上下文 + SQLite 中的近期对话历史构建系统提示词
4. 通过 SSE 事件流式返回 LLM 回复（qwen-turbo 通过 DashScope）
5. 成功后，将助手消息持久化到 SQLite

**核心模块：**
| 模块 | 职责 |
|---|---|
| `app/api/chat.py` | REST 接口：`POST /chat`（SSE 流）、`POST /upload`、`GET /history`、`GET/POST/DELETE /sessions` |
| `app/services/multimodal_service.py` | RAG 核心编排 — 串联图片处理、检索、LLM 调用和 SSE 流式输出 |
| `app/core/vision.py` | 调用 Qwen-VL（`dashscope.MultiModalConversation`）描述图片；模型由 `LLM_MODEL` 环境变量决定 |
| `app/core/ocr.py` | 延迟初始化 PaddleOCR 进行中文文字提取；未安装时优雅降级 |
| `app/core/config.py` | 通过 python-dotenv 加载 `.env`；暴露 `settings` 单例 |
| `app/database/chroma_store.py` | ChromaDB 持久化客户端（`my_vector_db/`），使用 ModelScope 下载的 BGE-small-zh-v1.5 嵌入，支持 upsert/query |
| `app/database/sqlite_store.py` | SQLite（`app/database/rag_system.db`）— sessions + chat_messages 表，完整 CRUD |

**运行时数据目录（已 gitignore，运行时自动创建）：**
- `uploads/` — 以 UUID 文件名存储的上传图片
- `my_vector_db/` — ChromaDB 持久化索引
- `app/database/rag_system.db` — SQLite 数据库文件

**前端：** `index.html` — 单页聊天界面，包含图片上传按钮、通过 `fetch` + `ReadableStream` 实现的 SSE 流式接收、`marked.js` 渲染 Markdown。通过 `/api/upload`、`/api/chat`、`/api/history` 与后端通信。

## 环境变量（.env）

| 变量 | 用途 | 默认值 |
|---|---|---|
| `DASHSCOPE_API_KEY` | 阿里云 DashScope API 密钥（必填） | — |
| `LLM_MODEL` | 用于图片描述的视觉模型 | `qwen-vl-plus` |
| `OCR_LANG` | PaddleOCR 语言 | `ch` |

聊天回复使用的 LLM 在 `multimodal_service.py` 中硬编码为 `qwen-turbo`（不受 `LLM_MODEL` 控制）。

## 关键实现细节

- **PaddleOCR 是可选的。** 若导入或初始化失败，`extract_text()` 返回空字符串 — 系统回退到仅用视觉描述。Python 3.13+ 用户会走这条路径，因为 `requirements.txt` 中 PaddleOCR 已被注释掉。
- **ChromaDB 嵌入函数** 首次运行时通过 ModelScope `snapshot_download` 拉取 `BAAI/bge-small-zh-v1.5`。如果 ModelScope 不可达，`ef` 为 `None`，ChromaDB 回退到其默认嵌入函数。
- **向量 ID 是内容寻址的** — `doc_{索引}_{sha256前16位}` — 因此重复摄入相同内容会执行 upsert 而非产生重复数据。
- **会话标题** 从第一条用户消息自动设置（取前 20 个字符）。无消息的会话显示"新对话"。
- **SSE 格式：** `data: [STATUS]: ...` 表示状态更新，`data: [THINKING]: ...` 表示思考中，`data: [SOURCE]: ...` 表示上下文来源，纯 `data: ...` 表示流式回答片段（每次 6 个字符）。
- **全局偏好：** 参见 `~/.claude/CLAUDE.md`（中文回复 + 每行代码写注释）。
