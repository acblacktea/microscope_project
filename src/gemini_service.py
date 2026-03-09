from google import genai
from google.genai import types

GEMINI_API_KEY = ""
GEMINI_MODEL = "gemini-2.5-flash"

ANALYSIS_PROMPT = """你是一位专业的水产养殖藻类分析专家。请分析以下显微镜拍摄的藻类样本图片（共5张，每隔1秒采集一张）。

请严格按照以下HTML格式输出分析报告，不要输出markdown，直接输出HTML片段（不需要html/body标签）：

<h2>藻类种类识别</h2>
用简短的无序列表列出识别到的藻类，每种只需一行：中文名（学名），一句话描述特征。不要长篇大论。

<h2>各种类占比估算</h2>
用HTML表格展示，表格有三列：种类、估算占比、状态评估。状态评估一句话即可。示例格式：
<table>
<tr><th>种类</th><th>估算占比</th><th>状态评估</th></tr>
<tr><td>绿藻类</td><td>70%-75%</td><td>以小球藻为主，水色呈现较好的绿色。</td></tr>
</table>

<h2>水质诊断</h2>
用2-3个要点简短总结：藻相评价、密度评估、整体水质评分（1-10分）。每个要点一句话。

<h2>建议操作</h2>
用简短的无序列表给出3-5条具体可操作的养殖建议。每条建议一句话，直接说该做什么。

要求：简洁精炼，避免冗长描述，重点突出数据和结论。用中文回答。"""


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
