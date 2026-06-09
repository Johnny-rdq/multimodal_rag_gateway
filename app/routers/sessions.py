# app/routers/sessions.py
from fastapi import APIRouter
# 直接引入你亲自写的数据库操作函数
from app.database.sqlite_store import get_all_sessions, get_all_messages, delete_session

router = APIRouter(prefix="/api/sessions", tags=["Session Management"])

@router.get("")
def get_sessions_api():
    """获取所有会话列表"""
    try:
        # 调用你的函数
        sessions = get_all_sessions() 
        # 适配前端需要的数据格式: {"id": "...", "title": "..."}
        formatted_sessions = [{"id": s["session_id"], "title": s["title"]} for s in sessions]
        return {"sessions": formatted_sessions}
    except Exception as e:
        print(f"[ERROR] 会话列表加载失败: {e}")
        return {"sessions": []}

@router.get("/{session_id}")
def get_session_history_api(session_id: str):
    """获取特定会话的历史消息"""
    try:
        # 调用你的函数
        messages = get_all_messages(session_id)
        return {"history": messages}
    except Exception as e:
        print(f"[ERROR] 历史消息加载失败: {e}")
        return {"history": []}

@router.delete("/{session_id}")
def delete_session_api(session_id: str):
    """删除特定会话"""
    try:
        # 调用你的函数
        delete_session(session_id)
        return {"status": "success"}
    except Exception as e:
        print(f"[ERROR] 会话删除失败: {e}")
        return {"status": "error"}