# app/agents/agent_router.py
import dashscope
from app.core.config import settings

dashscope.api_key = settings.DASHSCOPE_API_KEY


def determine_route(query: str, has_current_file: bool) -> str:
    """智能路由中心"""
    if has_current_file:
        print("[Router] 发现新文件，强制走 vision 分支")
        return "vision"

    # 强化提示词，强制 AI 只能输出一个词
    system_prompt = """
    你是一个极其严格的意图识别引擎。请根据用户的提问，仅仅输出一个英文单词来代表分类：
    - 如果用户询问今天的新闻、最新的股票、天气或需要查阅最新互联网资讯，输出 "search"
    - 如果用户询问特定的知识、文档内容、或需要查本地知识库，输出 "rag"
    - 如果用户只是打招呼或日常闲聊，输出 "chat"

    警告：只允许输出 "search", "rag", 或 "chat" 这三个词之一，绝对不能包含任何标点符号或其他解释说明！
    """

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": query}
    ]

    try:
        response = dashscope.Generation.call(
            model="qwen-turbo",
            messages=messages,
            result_format="message"
        )
        if response.status_code == 200:
            intent = response.output.choices[0].message.content.strip().lower()
            # 👇 加上这行打印，我们就能在终端看到 AI 到底判断成了什么！
            print(f"\n[Router] AI 判定当前意图为: ===> {intent} <===")

            if "search" in intent:
                return "search"
            elif "chat" in intent:
                return "chat"
    except Exception as e:
        print(f"[Router Error] 路由判断失败: {e}")

    print("[Router] 未命中规则，默认走 rag 分支")
    return "rag"