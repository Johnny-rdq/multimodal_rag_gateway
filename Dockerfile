# ============================================
# Nexus AI Engine — 多模态 RAG 网关 Docker 镜像
# ============================================
# 运行时平台：Railway / Render 或本地 Docker
# 基础镜像：Python 3.11-slim（兼容 ChromaDB + PaddleOCR）

FROM python:3.12-slim-bookworm

# ---- 系统依赖 ----
# libgl1：OpenCV/Pillow 依赖（Bookworm 起改名）
# libgomp1：ChromaDB / sentence-transformers 依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# ---- 设置工作目录 ----
WORKDIR /app

# ---- 安装 Python 依赖 ----
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ---- 预下载 BGE 嵌入模型（避免首次启动等待） ----
RUN python -c "from modelscope import snapshot_download; snapshot_download('BAAI/bge-small-zh-v1.5')"

# ---- 复制应用代码 ----
COPY . .

# ---- 创建持久化目录 + 非 root 用户 ----
RUN mkdir -p /app/uploads /app/my_vector_db /app/app/database \
    && useradd -m appuser \
    && chown -R appuser:appuser /app
USER appuser

# ---- 启动命令 ----
# Railway/Render 会自动注入 $PORT 环境变量（默认 8000）
# 本地运行可设置 PORT=8001
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
