import time
import base64
from openai import OpenAI

from config import DOUBAO_API_KEY, DOUBAO_MODEL, SHRIMP_PROMPT


def analyze_images_doubao(image_data_list: list[bytes]) -> str:
    """
    调用豆包 Vision API 分析多张显微镜图片（虾体分析）。

    Args:
        image_data_list: PNG 格式图片字节数据列表

    Returns:
        豆包返回的分析报告文本
    """
    if not DOUBAO_API_KEY:
        return "错误：未配置豆包 API Key，请在 config.py 中填写 DOUBAO_API_KEY。"

    client = OpenAI(
        api_key=DOUBAO_API_KEY,
        base_url="https://ark.cn-beijing.volces.com/api/v3",
    )

    content = [{"type": "text", "text": SHRIMP_PROMPT}]
    for img_data in image_data_list:
        b64 = base64.b64encode(img_data).decode("utf-8")
        content.append({
            "type": "image_url",
            "image_url": {
                "url": f"data:image/png;base64,{b64}",
            },
        })

    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model=DOUBAO_MODEL,
                messages=[
                    {"role": "user", "content": content},
                ],
            )
            return response.choices[0].message.content
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
                continue
            raise
