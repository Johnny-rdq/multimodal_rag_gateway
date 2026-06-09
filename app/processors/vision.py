"""视觉理解 — 调用 Qwen-VL 多模态模型对图片进行描述和问答
- analyze_image: 通用图片分析，可自定义提问
- describe_image_for_embedding: 生成详细描述，用于存入向量库做 RAG 检索
"""
import dashscope
from app.core.config import settings
import base64

dashscope.api_key = settings.DASHSCOPE_API_KEY


def analyze_image(image_path: str, question: str = "请详细描述这张图片的内容") -> str:
    """用 Qwen-VL 理解图片内容，返回文字描述
    将图片转 base64 编码后通过 DashScope MultiModalConversation API 发送
    """
    # 将图片文件转为 base64 字符串
    with open(image_path, "rb") as f:
        image_base64 = base64.b64encode(f.read()).decode()

    # 构建多模态消息：图片 + 文本提问
    messages = [{
        "role": "user",
        "content": [
            {"image": f"data:image/jpeg;base64,{image_base64}"},
            {"text": question}
        ]
    }]

    # 调用 DashScope 多模态对话 API
    response = dashscope.MultiModalConversation.call(
        model=settings.DEFAULT_MODEL,
        messages=messages
    )

    if response.status_code == 200:
        return response.output.choices[0].message.content[0]["text"]
    return f"图片分析失败: {response.message}"


def describe_image_for_embedding(image_path: str) -> str:
    """生成用于向量检索的图片描述（要求全面描述内容、文字、人物、场景）"""
    prompt = "请用一段中文详细描述这张图片的内容、文字、人物、场景等所有信息"
    return analyze_image(image_path, prompt)
