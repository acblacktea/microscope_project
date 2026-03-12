import time
from google import genai
from google.genai import types

from config import GEMINI_API_KEY, GEMINI_MODEL, PROMPTS, ALGAE_PROMPT


def analyze_images(image_data_list: list[bytes], mode: str = "algae") -> str:
    """
    调用 Gemini Vision API 分析多张显微镜图片。

    Args:
        image_data_list: PNG 格式图片字节数据列表
        mode: 分析模式，"algae" 或 "shrimp"

    Returns:
        Gemini 返回的分析报告文本
    """
    if not GEMINI_API_KEY:
        return "错误：未配置 Gemini API Key，请在 config.py 中填写 GEMINI_API_KEY。"

    client = genai.Client(api_key=GEMINI_API_KEY)

    prompt = PROMPTS.get(mode, ALGAE_PROMPT)
    contents = [prompt]
    for img_data in image_data_list:
        contents.append(types.Part.from_bytes(data=img_data, mime_type="image/png"))

    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model=GEMINI_MODEL,
                contents=contents,
            )
            return response.text
        except Exception as e:
            if '503' in str(e) and attempt < max_retries - 1:
                time.sleep(2 ** attempt)
                continue
            raise
