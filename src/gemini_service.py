from google import genai
from google.genai import types

GEMINI_API_KEY = ""
GEMINI_MODEL = "gemini-2.5-flash"

ANALYSIS_PROMPT = """你是一位专业的微生物学家和水产养殖专家。请分析以下显微镜拍摄的藻类样本图片（共5张，每隔1秒采集一张）。

请根据图片内容，给出以下分析报告：

## 藻类种类识别
列出图片中观察到的所有藻类种类，并描述其形态特征。

## 藻类浓度估算
对每种识别到的藻类，估算其大致浓度（cells/mL），并说明整体藻类密度水平（低/中/高）。

## 健康度评估
- 整体水质健康度评分（1-10分）
- 是否存在有害藻类（如蓝绿藻/微囊藻等）
- 藻类多样性评价

## 养殖建议
根据当前藻类状况，给出具体的水产养殖管理建议，包括：
- 是否需要调水
- 是否需要补充有益藻类
- 投喂建议
- 其他注意事项

请用中文回答，格式清晰，条理分明。"""


def analyze_images(image_data_list: list[bytes]) -> str:
    """
    调用 Gemini Vision API 分析多张显微镜图片。

    Args:
        image_data_list: PNG 格式图片字节数据列表

    Returns:
        Gemini 返回的分析报告文本
    """
    if not GEMINI_API_KEY:
        return "错误：未配置 Gemini API Key，请在 gemini_service.py 中填写 GEMINI_API_KEY。"

    client = genai.Client(api_key=GEMINI_API_KEY)

    contents = [ANALYSIS_PROMPT]
    for img_data in image_data_list:
        contents.append(types.Part.from_bytes(data=img_data, mime_type="image/png"))

    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=contents,
    )

    return response.text
