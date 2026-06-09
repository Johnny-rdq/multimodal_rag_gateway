"""SQLite 会话管理 — 存储对话会话和聊天消息
- sessions 表：会话 ID + 标题 + 创建/更新时间
- chat_messages 表：消息 ID + 所属会话 + 角色 + 内容 + 上下文来源 + 图片路径
- 会话标题自动取第一条用户消息前 20 个字符
"""
import sqlite3
import os
import uuid
from app.core.logger import logger

# 👇 加上绝对路径锁定，彻底防止 "unable to open database file"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "rag_system.db")

def init_db():
    """初始化数据库 — 创建 sessions 和 chat_messages 表（如果不存在）"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sessions (
            session_id TEXT PRIMARY KEY,
            title TEXT DEFAULT '新对话',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS chat_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT,
            role TEXT,
            content TEXT,
            context TEXT DEFAULT '',
            image_path TEXT DEFAULT '',
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (session_id) REFERENCES sessions(session_id)
        )
    ''')

    # 向后兼容：旧版数据库可能没有 image_path 列
    try:
        cursor.execute("SELECT image_path FROM chat_messages LIMIT 1")
    except sqlite3.OperationalError:
        cursor.execute("ALTER TABLE chat_messages ADD COLUMN image_path TEXT DEFAULT ''")

    conn.commit()
    conn.close()
    logger.info("SQLite 数据库初始化完成并准备就绪！")
    
def ensure_session_exists(session_id: str):
    """确保会话存在，不存在则自动创建"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT session_id FROM sessions WHERE session_id = ?", (session_id,))
    if not cursor.fetchone():
        cursor.execute("INSERT INTO sessions (session_id, title) VALUES (?, ?)", (session_id, "新对话"))
        conn.commit()
    conn.close()

def save_message(session_id: str, role: str, content: str, context: str = "", image_path: str = ""):
    """保存一条聊天消息，同时自动更新会话标题和更新时间"""
    ensure_session_exists(session_id)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO chat_messages (session_id, role, content, context, image_path) VALUES (?, ?, ?, ?, ?)",
        (session_id, role, content, context, image_path)
    )
    if role == "user":
        # 首条用户消息的前 20 个字符作为会话标题
        cursor.execute(
            "UPDATE sessions SET title = ?, updated_at = CURRENT_TIMESTAMP WHERE session_id = ? AND title = '新对话'",
            (content[:20], session_id)
        )
    else:
        cursor.execute("UPDATE sessions SET updated_at = CURRENT_TIMESTAMP WHERE session_id = ?", (session_id,))
    conn.commit()
    conn.close()

def get_all_messages(session_id: str) -> list:
    """获取指定会话的全部消息（按时间升序）"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT role, content, context, image_path FROM chat_messages WHERE session_id = ? ORDER BY timestamp ASC",
        (session_id,)
    )
    rows = cursor.fetchall()
    conn.close()
    return [{"role": r[0], "content": r[1], "context": r[2] or "", "image_path": r[3] or ""} for r in rows]

def get_recent_messages(session_id: str, limit: int = 6) -> list:
    """获取最近 N 条消息，用于构建 LLM 上下文（先降序取最新，再反转恢复时间顺序）"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT role, content FROM chat_messages WHERE session_id = ? ORDER BY timestamp DESC LIMIT ?",
        (session_id, limit)
    )
    rows = cursor.fetchall()
    conn.close()
    rows.reverse()
    return [{"role": r[0], "content": r[1]} for r in rows]

def get_all_sessions() -> list:
    """获取所有会话列表（按最后更新时间降序）"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT session_id, title FROM sessions ORDER BY updated_at DESC")
    rows = cursor.fetchall()
    conn.close()
    return [{"session_id": r[0], "title": r[1]} for r in rows]

def create_session() -> dict:
    """创建新会话，返回 12 位随机会话 ID"""
    session_id = uuid.uuid4().hex[:12]
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO sessions (session_id, title) VALUES (?, ?)", (session_id, "新对话"))
    conn.commit()
    conn.close()
    return {"session_id": session_id, "title": "新对话"}

def delete_session(session_id: str):
    """删除会话及其所有关联消息（先删消息再删会话，遵守外键约束）"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM chat_messages WHERE session_id = ?", (session_id,))
    cursor.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))
    conn.commit()
    conn.close()

# 👇 核心：每次模块加载时自动建表防错
init_db()