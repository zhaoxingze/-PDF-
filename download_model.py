"""
手动下载翻译模型脚本
如果网络无法访问Hugging Face，可以使用此脚本下载模型
"""
import os
import sys

def download_model():
    """下载模型到本地"""
    model_name = "Helsinki-NLP/opus-mt-en-zh"
    cache_dir = os.path.join(os.path.dirname(__file__), "models")

    print("=" * 50)
    print("翻译模型下载工具")
    print("=" * 50)
    print()
    print(f"模型: {model_name}")
    print(f"保存位置: {cache_dir}")
    print()

    # 创建目录
    os.makedirs(cache_dir, exist_ok=True)

    try:
        from transformers import MarianMTModel, MarianTokenizer

        print("正在下载tokenizer...")
        tokenizer = MarianTokenizer.from_pretrained(model_name)
        tokenizer.save_pretrained(os.path.join(cache_dir, "tokenizer"))
        print("tokenizer下载完成!")

        print("正在下载模型...")
        model = MarianMTModel.from_pretrained(model_name)
        model.save_pretrained(os.path.join(cache_dir, "model"))
        print("模型下载完成!")

        print()
        print("=" * 50)
        print("下载完成！现在可以运行翻译程序了。")
        print("=" * 50)

    except Exception as e:
        print(f"下载失败: {e}")
        print()
        print("解决方案：")
        print("1. 使用VPN或代理")
        print("2. 使用百度翻译API（推荐）")
        print("3. 手动下载模型文件")

if __name__ == "__main__":
    download_model()
