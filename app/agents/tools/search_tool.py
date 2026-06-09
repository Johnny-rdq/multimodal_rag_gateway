# app/agents/tools/search_tool.py
from tavily import TavilyClient
from app.core.config import settings

# 确保在 settings.py 中配置了 TAVILY_API_KEY
client = TavilyClient(api_key=settings.TAVILY_API_KEY)


def search_web(query: str, max_results: int = 3) -> str:
    """
    Agent 工具：使用 Tavily 专业的 AI 搜索引擎进行联网查询
    """
    try:
        # search_depth="advanced" 会让它搜索更深入，且返回更全面的内容
        response = client.search(query, search_depth="advanced", max_results=max_results)

        results = []
        for res in response.get("results", []):
            results.append(f"【来源】{res['title']}\n【内容】{res['content']}\n【链接】{res['url']}")

        print(f"[INFO] 成功通过 Tavily 获取到实时信息")
        return "\n\n".join(results)
    except Exception as e:
        print(f"[ERROR] Tavily 搜索失败: {e}")
        return "未能联网获取到实时资讯。"