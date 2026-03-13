"""测试豆包虾体分析接口"""
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from doubao_service import analyze_images_doubao

IMAGE_PATHS = ["shrimp.jpeg", "shrimp2.jpg", "shrimp3.jpg", "shrimp4.jpg"]

if __name__ == "__main__":
    image_data_list = []
    for path in IMAGE_PATHS:
        if not os.path.exists(path):
            print(f"图片不存在: {path}")
            sys.exit(1)
        with open(path, "rb") as f:
            image_data_list.append(f.read())
        print(f"已加载: {path}")

    print(f"共加载 {len(image_data_list)} 张图片，正在调用豆包 API 分析...")
    try:
        result = analyze_images_doubao(image_data_list)
        print("=== 分析结果 ===")
        print(result)
    except Exception as e:
        print(f"调用失败: {e}")
