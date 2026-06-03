import os
import json
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
APP_NAME = "PDF论文翻译工具"


def is_frozen_app():
    """Return True when running from a PyInstaller executable."""
    return bool(getattr(sys, "frozen", False))


def resource_path(relative_path):
    """Resolve bundled resources in source and PyInstaller builds."""
    if is_frozen_app() and hasattr(sys, "_MEIPASS"):
        base_dir = sys._MEIPASS
    else:
        base_dir = BASE_DIR
    return os.path.join(base_dir, relative_path)


def get_config_dir():
    """Use AppData for installed builds and the project folder for source runs."""
    if is_frozen_app():
        local_appdata = os.environ.get("LOCALAPPDATA")
        if local_appdata:
            return os.path.join(local_appdata, APP_NAME)
    return BASE_DIR


CONFIG_FILE = os.path.join(get_config_dir(), "api_config.json")

# API配置
API_CONFIG = {
    "translator_type": "google",  # google, baidu 或 local
    "local_model": "Helsinki-NLP/opus-mt-en-zh",
    "baidu_translate_app_id": "",
    "baidu_translate_secret_key": "",
    "baidu_ocr_api_key": "",
    "baidu_ocr_secret_key": "",
    "use_ocr": False,
    "ocr_type": "baidu",  # baidu 或 local
}

def load_api_config():
    """加载API配置"""
    global API_CONFIG
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                saved = json.load(f)
                API_CONFIG.update(saved)
        except:
            pass
    return API_CONFIG

def save_api_config(config):
    """保存API配置"""
    global API_CONFIG
    API_CONFIG.update(config)
    os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(API_CONFIG, f, ensure_ascii=False, indent=2)

# 兼容旧代码
BAIDU_CONFIG = {
    "app_id": "",
    "secret_key": "",
}

def get_translate_config():
    """获取翻译配置"""
    return {
        "app_id": API_CONFIG.get("baidu_translate_app_id", ""),
        "secret_key": API_CONFIG.get("baidu_translate_secret_key", ""),
    }

def get_ocr_config():
    """获取OCR配置"""
    return {
        "api_key": API_CONFIG.get("baidu_ocr_api_key", ""),
        "secret_key": API_CONFIG.get("baidu_ocr_secret_key", ""),
        "use_ocr": API_CONFIG.get("use_ocr", False),
        "ocr_type": API_CONFIG.get("ocr_type", "baidu"),
    }

# 字体配置
FONT_CONFIG = {
    "default_font": resource_path(os.path.join("fonts", "NotoSansSC-Regular.ttf")),
    "fallback_font": "china-s",
}

# GUI配置
GUI_CONFIG = {
    "window_title": "PDF论文翻译工具",
    "window_size": "900x760",
}

# 启动时加载配置
load_api_config()
