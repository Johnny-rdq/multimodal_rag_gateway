"""多模态向量存储 — 文本 + 图片描述混合检索"""
import os
import hashlib
import chromadb
from chromadb.utils import embedding_functions

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "my_vector_db")


def _get_embedding_function():
    try:
        from modelscope import snapshot_download
        model_dir = snapshot_download("BAAI/bge-small-zh-v1.5")
        return embedding_functions.SentenceTransformerEmbeddingFunction(model_name=model_dir, device="cpu")
    except Exception:
        return None


ef = _get_embedding_function()
chroma_client = chromadb.PersistentClient(path=DB_PATH)

try:
    knowledge_collection = chroma_client.get_collection(name="multimodal_docs", embedding_function=ef)
except Exception:
    try:
        chroma_client.delete_collection(name="multimodal_docs")
    except Exception:
        pass
    knowledge_collection = chroma_client.create_collection(name="multimodal_docs", embedding_function=ef)


def _stable_id(text: str, index: int) -> str:
    h = hashlib.sha256(text.encode()).hexdigest()[:16]
    return f"doc_{index}_{h}"


def add_to_db(texts: list[str], metadatas: list[dict] = None):
    """写入向量库，metadatas 可存图片路径等"""
    if not texts:
        return
    ids = [_stable_id(t, i) for i, t in enumerate(texts)]
    knowledge_collection.upsert(documents=texts, ids=ids, metadatas=metadatas)
    print(f"[INFO] {len(texts)} chunks written to multimodal vector DB")


def query_db(query: str, n_results: int = 3) -> list[str]:
    if knowledge_collection.count() == 0:
        return []
    try:
        results = knowledge_collection.query(query_texts=[query], n_results=n_results)
        if results.get("documents") and results["documents"][0]:
            return results["documents"][0]
    except Exception as e:
        print(f"[ERROR] Query failed: {e}")
    return []


def get_all_docs() -> list[str]:
    try:
        return knowledge_collection.get()["documents"] or []
    except Exception:
        return []
