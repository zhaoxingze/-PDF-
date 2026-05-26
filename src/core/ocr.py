import base64
import hashlib
import random
import time
import json
from typing import List, Tuple, Optional
import requests
from PIL import Image
import io


class BaiduOCR:
    """百度OCR API"""

    def __init__(self, api_key: str = "", secret_key: str = ""):
        self.api_key = api_key
        self.secret_key = secret_key
        self.access_token = None
        self.token_url = "https://aip.baidubce.com/oauth/2.0/token"
        self.ocr_url = "https://aip.baidubce.com/rest/2.0/ocr/v1/general_basic"

    def get_access_token(self) -> str:
        """获取access_token"""
        if self.access_token:
            return self.access_token

        params = {
            "grant_type": "client_credentials",
            "client_id": self.api_key,
            "client_secret": self.secret_key,
        }

        response = requests.post(self.token_url, params=params)
        result = response.json()

        if "access_token" in result:
            self.access_token = result["access_token"]
            return self.access_token
        else:
            raise Exception(f"获取token失败: {result}")

    def recognize(self, image_bytes: bytes) -> str:
        """识别图片中的文字"""
        if not self.api_key or not self.secret_key:
            return ""

        try:
            token = self.get_access_token()
            img_base64 = base64.b64encode(image_bytes).decode()

            params = {"image": img_base64}
            headers = {"Content-Type": "application/x-www-form-urlencoded"}

            response = requests.post(
                f"{self.ocr_url}?access_token={token}",
                data=params,
                headers=headers,
            )
            result = response.json()

            if "words_result" in result:
                lines = [item["words"] for item in result["words_result"]]
                return "\n".join(lines)
            else:
                return ""
        except Exception as e:
            return f"[OCR错误: {str(e)}]"


class LocalOCR:
    """本地Tesseract OCR"""

    def __init__(self, lang: str = "eng"):
        self.lang = lang
        self._available = None

    def is_available(self) -> bool:
        """检查Tesseract是否可用"""
        if self._available is not None:
            return self._available

        try:
            import pytesseract
            pytesseract.get_tesseract_version()
            self._available = True
        except Exception:
            self._available = False

        return self._available

    def recognize(self, image_bytes: bytes) -> str:
        """识别图片中的文字"""
        if not self.is_available():
            return "[Tesseract未安装]"

        try:
            import pytesseract
            image = Image.open(io.BytesIO(image_bytes))
            text = pytesseract.image_to_string(image, lang=self.lang)
            return text.strip()
        except Exception as e:
            return f"[OCR错误: {str(e)}]"


class OCRFactory:
    """OCR工厂"""

    @staticmethod
    def create(ocr_type: str = "baidu", **kwargs):
        """创建OCR实例"""
        if ocr_type == "baidu":
            return BaiduOCR(
                api_key=kwargs.get("api_key", ""),
                secret_key=kwargs.get("secret_key", ""),
            )
        elif ocr_type == "local":
            return LocalOCR(lang=kwargs.get("lang", "eng"))
        else:
            raise ValueError(f"不支持的OCR类型: {ocr_type}")
