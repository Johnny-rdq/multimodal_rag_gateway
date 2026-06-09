"""ChromaDB 向量存储 — 文本 + 图片描述混合语义检索
- 使用 BGE-small-zh-v1.5 中文嵌入模型（通过 ModelScope 下载）
- 内容寻址 ID（SHA256 前16位），重复内容 upsert 不会产生冗余
- 持久化存储在项目根目录 my_vector_db/
"""
import os
import hashlib
import chromadb
from chromadb.utils import embedding_functions

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "my_vector_db")


def _get_embedding_function():
    """获取嵌入函数 — 优先使用 BGE 中文模型，失败则回退到 ChromaDB 默认"""
    try:
        from modelscope import snapshot_download
        model_dir = snapshot_download("BAAI/bge-small-zh-v1.5")
        return embedding_functions.SentenceTransformerEmbeddingFunction(model_name=model_dir, device="cpu")
    except Exception:
        return None


# 初始化嵌入函数和 ChromaDB 客户端
ef = _get_embedding_function()
chroma_client = chromadb.PersistentClient(path=DB_PATH)

# 获取或创建 multimodal_docs 集合
try:
    knowledge_collection = chroma_client.get_collection(name="multimodal_docs", embedding_function=ef)
except Exception:
    try:
        chroma_client.delete_collection(name="multimodal_docs")
    except Exception:
        pass
    knowledge_collection = chroma_client.create_collection(name="multimodal_docs", embedding_function=ef)


def _stable_id(text: str, index: int) -> str:
    """生成内容寻址的唯一 ID：doc_索引_内容SHA256前16位
    相同内容生成相同 ID，upsert 时自动去重
    """
    h = hashlib.sha256(text.encode()).hexdigest()[:16]
    return f"doc_{index}_{h}"


def add_to_db(texts: list[str], metadatas: list[dict] = None):
    """将文本块写入向量库，metadatas 可附加图片路径等信息"""
    if not texts:
        return
    ids = [_stable_id(t, i) for i, t in enumerate(texts)]
    knowledge_collection.upsert(documents=texts, ids=ids, metadatas=metadatas)
    print(f"[INFO] {len(texts)} chunks written to multimodal vector DB")


# 修改 app/database/chroma_store.py 中的 query_db 函数
def query_db(query: str, n_results: int = 3, where_filter: dict = None) -> list[str]:
    if knowledge_collection.count() == 0:
        return []
    try:
        # 动态构建查询参数
        kwargs = {"query_texts": [query], "n_results": n_results}
        if where_filter:
            kwargs["where"] = where_filter  # 👈 核心：加上条件过滤

        results = knowledge_collection.query(**kwargs)
        if results.get("documents") and results["documents"][0]:
            return results["documents"][0]
    except Exception as e:
        print(f"[ERROR] Query failed: {e}")
    return []


def get_all_docs() -> list[str]:
    """获取向量库中的所有文档"""
    try:
        return knowledge_collection.get()["documents"] or []
    except Exception:
        return []
