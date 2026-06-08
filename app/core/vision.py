"""视觉理解 — Qwen-VL 多模态模型"""
import dashscope
from app.core.config import settings
import base64

dashscope.api_key = settings.DASHSCOPE_API_KEY


def analyze_image(image_path: str, question: str = "请详细描述这张图片的内容") -> str:
    """
    用 Qwen-VL 理解图片，返回文字描述
    image_path: 本地图片路径
    question: 对图片的提问
    """
    with open(image_path, "rb") as f:
        image_base64 = base64.b64encode(f.read()).decode()

    messages = [{
        "role": "user",
        "content": [
            {"image": f"data:image/jpeg;base64,{image_base64}"},
            {"text": question}
        ]
    }]

    response = dashscope.MultiModalConversation.call(
        model=settings.DEFAULT_MODEL,
        messages=messages
    )

    if response.status_code == 200:
        return response.output.choices[0].message.content[0]["text"]
    return f"图片分析失败: {response.message}"


def describe_image_for_embedding(image_path: str) -> str:
    """生成用于向量检索的图片描述"""
    prompt = "请用一段中文详细描述这张图片的内容、文字、人物、场景等所有信息"
    return analyze_image(image_path, prompt)
