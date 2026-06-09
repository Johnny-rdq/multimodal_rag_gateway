# Nexus AI Engine — 多模态 RAG 网关

基于 FastAPI 的智能对话引擎，支持图片、PDF、Office 文档等多种格式的上传与理解，结合本地向量检索和全网实时搜索，通过大模型流式生成回答。

## 功能特性

- **多模态文件理解** — 支持图片（JPG/PNG）、PDF、TXT、Word（DOCX）上传，自动 OCR 文字提取 + 视觉模型描述
- **智能路由分流** — AI 自动判断用户意图，将问题分发到文档分析 / 本地知识检索 / 全网实时搜索三个分支
- **向量语义检索** — ChromaDB + BGE 中文嵌入模型，内容寻址去重
- **流式对话** — SSE（Server-Sent Events）流式输出，打字机效果实时显示
- **会话管理** — SQLite 持久化存储，支持多会话切换、历史回溯
- **联网搜索** — 接入 Tavily Search API，获取最新资讯

## 架构概览

```
用户上传文件 / 提问
        │
        ▼
┌──────────────────┐
│   智能路由 Agent   │  ← 判断意图：vision / rag / search
└──────┬───────────┘
       │
   ┌───┼───┐
   ▼   ▼   ▼
┌────┐┌────┐┌──────┐
│文档 ││向量 ││全网   │
│解析 ││检索 ││搜索   │
└──┬─┘└──┬─┘└──┬───┘
   │     │      │
   └─────┼──────┘
         ▼
   ┌──────────┐
   │  LLM 回答 │  ← qwen-turbo 流式生成
   └──────────┘
```

### 目录结构

```
app/
├── main.py              # FastAPI 入口，挂载路由
├── agents/
│   ├── agent_router.py  # 智能路由：根据意图分流
│   └── tools/
│       └── search_tool.py # Tavily 全网搜索工具
├── api/
│   └── chat.py          # 聊天 + 上传 API
├── routers/
│   └── sessions.py      # 会话管理 API
├── services/
│   └── multimodal_service.py # RAG 核心流水线
├── processors/
│   ├── ocr.py           # PaddleOCR 文字提取
│   ├── vision.py        # Qwen-VL 视觉理解
│   ├── pdf_processor.py # PDF 解析（文字 + 图表）
│   └── text_processor.py # TXT / DOCX 解析
├── database/
│   ├── chroma_store.py  # ChromaDB 向量存储
│   └── sqlite_store.py  # SQLite 会话管理
└── core/
    ├── config.py        # 环境变量配置
    └── logger.py        # 日志系统
```

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

在项目根目录创建 `.env` 文件：

```env
# 必填：阿里云 DashScope API Key
DASHSCOPE_API_KEY=sk-xxxxxxxxxxxxxxxx

# 可选：视觉模型（默认 qwen-vl-plus）
LLM_MODEL=qwen-vl-plus

# 可选：OCR 语言（默认 ch）
OCR_LANG=ch

# 可选：Tavily 搜索 API Key（不填则联网搜索不可用）
TAVILY_API_KEY=tvly-xxxxxxxxxxxxxxxx
```

> DashScope API Key 获取：https://dashscope.console.aliyun.com/
> Tavily API Key 获取：https://tavily.com/

### 3. 启动服务

```bash
python -m app.main
# 或
uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload
```

启动后访问 http://127.0.0.1:8001 即可使用。

## API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/` | 前端聊天界面 |
| `POST` | `/api/chat` | SSE 流式聊天 |
| `POST` | `/api/upload` | 文件上传（jpg/png/pdf/txt/docx） |
| `GET` | `/api/history?session_id=xxx` | 获取会话历史 |
| `GET` | `/api/sessions` | 获取所有会话 |
| `POST` | `/api/sessions` | 创建新会话 |
| `DELETE` | `/api/sessions/{id}` | 删除会话 |

## 技术栈

| 组件 | 技术 |
|------|------|
| Web 框架 | FastAPI + Uvicorn |
| 前端 | 原生 HTML + Tailwind CSS + marked.js |
| 大模型 | DashScope（qwen-turbo / qwen-vl-plus） |
| 向量数据库 | ChromaDB |
| 嵌入模型 | BGE-small-zh-v1.5（通过 ModelScope 下载） |
| 文件解析 | pdfplumber + python-docx + PaddleOCR |
| 搜索引擎 | Tavily Search API |
| 会话存储 | SQLite |

## 注意事项

- **PaddleOCR 仅支持 Python 3.12 及以下**，3.13+ 会自动跳过 OCR，回退为纯视觉理解
- **首次启动** 会自动从 ModelScope 下载 BGE 嵌入模型（约 100MB）
- **向量 ID 基于内容哈希**，重复上传相同内容不会产生冗余数据
- 运行时自动生成的目录（`uploads/`、`my_vector_db/`、`*.db`）已在 `.gitignore` 中排除
