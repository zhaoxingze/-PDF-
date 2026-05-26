import hashlib
import random
import time
from typing import List, Callable, Optional
import requests
import json


class BaiduTranslator:
    """百度翻译API"""

    def __init__(self, app_id: str = "", secret_key: str = ""):
        self.app_id = app_id
        self.secret_key = secret_key
        self.api_url = "https://fanyi-api.baidu.com/api/trans/vip/translate"

    def _make_sign(self, query: str, salt: str) -> str:
        sign_str = self.app_id + query + salt + self.secret_key
        return hashlib.md5(sign_str.encode()).hexdigest()

    def _get_error_msg(self, error_code: str) -> str:
        errors = {
            "52001": "请求超时",
            "52002": "系统错误",
            "52003": "未授权用户",
            "54000": "必填参数为空",
            "54001": "签名错误",
            "54003": "访问频率受限",
            "54004": "账户余额不足",
            "58000": "客户端IP非法",
            "90107": "认证未通过或未生效",
        }
        return errors.get(error_code, f"错误码{error_code}")

    def test_connection(self) -> str:
        """测试API连接"""
        result = self.translate_single("Hello")
        return result

    def translate_single(self, text: str) -> str:
        if not text.strip():
            return ""
        if not self.app_id or not self.secret_key:
            return "[请配置百度翻译API]"

        salt = str(random.randint(10000, 99999))
        sign = self._make_sign(text, salt)

        params = {
            "q": text,
            "from": "en",
            "to": "zh",
            "appid": self.app_id,
            "salt": salt,
            "sign": sign,
        }

        try:
            response = requests.get(self.api_url, params=params, timeout=15)
            result = response.json()

            if "trans_result" in result:
                return result["trans_result"][0]["dst"]
            elif "error_code" in result:
                return f"[{self._get_error_msg(result['error_code'])}]"
            else:
                return f"[未知响应]"
        except requests.exceptions.Timeout:
            return "[请求超时]"
        except requests.exceptions.ConnectionError:
            return "[网络连接失败]"
        except Exception as e:
            return f"[错误: {str(e)}]"

    def translate_batch(self, texts: List[str], batch_size: int = 10) -> List[str]:
        if not self.app_id or not self.secret_key:
            return ["[请配置百度翻译API]"] * len(texts)

        total = len(texts)
        translations = [""] * total

        # 过滤有效文本
        valid_items = []
        for i, text in enumerate(texts):
            stripped = text.strip()
            if stripped and len(stripped) > 1 and not stripped.isdigit():
                valid_items.append((i, stripped))

        # 逐条翻译
        for idx, (orig_idx, text) in enumerate(valid_items):
            # 频率限制
            time.sleep(1.0)

            salt = str(random.randint(10000, 99999))
            sign = self._make_sign(text, salt)

            params = {
                "q": text,
                "from": "en",
                "to": "zh",
                "appid": self.app_id,
                "salt": salt,
                "sign": sign,
            }

            try:
                response = requests.get(self.api_url, params=params, timeout=10)
                result = response.json()

                if "trans_result" in result:
                    translations[orig_idx] = result["trans_result"][0]["dst"]
                elif "error_code" in result:
                    translations[orig_idx] = f"[{self._get_error_msg(result['error_code'])}]"
                else:
                    translations[orig_idx] = "[翻译失败]"

            except Exception as e:
                translations[orig_idx] = "[网络错误]"

        return translations


class LocalTranslator:
    """本地翻译模型"""

    def __init__(self, model_name: str = "Helsinki-NLP/opus-mt-en-zh"):
        self.model_name = model_name
        self.model = None
        self.tokenizer = None
        self.device = None
        # 国内镜像源
        self.mirror_url = "https://hf-mirror.com"

    def load_model(self, progress_callback: Optional[Callable] = None):
        """加载模型"""
        try:
            import torch
            import os
            from transformers import MarianMTModel, MarianTokenizer

            if progress_callback:
                progress_callback("正在加载本地翻译模型...", 0)

            # 检测GPU
            if torch.cuda.is_available():
                self.device = "cuda"
                gpu_name = torch.cuda.get_device_name(0)
                if progress_callback:
                    progress_callback(f"检测到GPU: {gpu_name}", 30)
            else:
                self.device = "cpu"
                if progress_callback:
                    progress_callback("未检测到GPU，使用CPU（速度较慢）", 30)

            # 检查本地是否有下载好的模型
            local_model_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "models")
            local_tokenizer_dir = os.path.join(local_model_dir, "tokenizer")
            local_model_path = os.path.join(local_model_dir, "model")

            if os.path.exists(local_tokenizer_dir) and os.path.exists(local_model_path):
                # 从本地加载
                if progress_callback:
                    progress_callback("从本地加载模型...", 50)
                self.tokenizer = MarianTokenizer.from_pretrained(local_tokenizer_dir)
                self.model = MarianMTModel.from_pretrained(local_model_path)
            else:
                # 尝试在线下载
                if progress_callback:
                    progress_callback("正在下载模型...", 50)

                # 设置镜像源
                os.environ["HF_ENDPOINT"] = self.mirror_url

                try:
                    self.tokenizer = MarianTokenizer.from_pretrained(self.model_name)
                    self.model = MarianMTModel.from_pretrained(self.model_name)
                except Exception as e1:
                    if progress_callback:
                        progress_callback("镜像源失败，尝试官方源...", 60)
                    os.environ.pop("HF_ENDPOINT", None)
                    try:
                        self.tokenizer = MarianTokenizer.from_pretrained(self.model_name)
                        self.model = MarianMTModel.from_pretrained(self.model_name)
                    except Exception as e2:
                        raise Exception(
                            "模型下载失败！\n\n"
                            "解决方案：\n"
                            "1. 运行 python download_model.py 手动下载\n"
                            "2. 使用百度翻译API（推荐，无需下载）\n"
                            "3. 使用VPN/代理后重试"
                        )

            self.model.to(self.device)
            self.model.eval()

            # 启用半精度加速（GPU）
            if self.device == "cuda":
                self.model = self.model.half()
                if progress_callback:
                    progress_callback("已启用GPU半精度加速", 80)

            if progress_callback:
                progress_callback(f"模型加载完成 ({self.device.upper()})", 100)

        except ImportError:
            raise Exception("需要安装torch和transformers: pip install torch transformers")
        except Exception as e:
            raise Exception(f"模型加载失败: {str(e)}")

    def test_connection(self) -> str:
        """测试本地模型"""
        try:
            if self.model is None:
                self.load_model()
            result = self.translate_single("Hello")
            return result
        except Exception as e:
            return f"[模型加载失败: {str(e)}]"

    def translate_single(self, text: str) -> str:
        if not text.strip():
            return ""
        if self.model is None:
            self.load_model()

        import torch
        inputs = self.tokenizer(text, return_tensors="pt", padding=True, truncation=True, max_length=128).to(self.device)
        with torch.no_grad():
            outputs = self.model.generate(**inputs, num_beams=1, max_length=128)
        translated = self.tokenizer.batch_decode(outputs, skip_special_tokens=True)
        return translated[0] if translated else ""

    def translate_batch(self, texts: List[str], batch_size: int = 64) -> List[str]:
        if self.model is None:
            self.load_model()

        import torch
        total = len(texts)
        translations = [""] * total

        # 过滤有效文本
        valid_items = []
        for i, text in enumerate(texts):
            stripped = text.strip()
            if stripped and len(stripped) > 1:
                valid_items.append((i, stripped))

        # GPU使用更大批量
        if self.device == "cuda":
            batch_size = 128

        # 批量翻译
        for batch_start in range(0, len(valid_items), batch_size):
            batch_items = valid_items[batch_start:batch_start + batch_size]
            batch_texts = [text for _, text in batch_items]

            inputs = self.tokenizer(
                batch_texts,
                return_tensors="pt",
                padding=True,
                truncation=True,
                max_length=128,
            ).to(self.device)

            with torch.no_grad():
                outputs = self.model.generate(
                    **inputs,
                    num_beams=1,
                    max_length=128,
                    do_sample=False,
                )

            translated = self.tokenizer.batch_decode(outputs, skip_special_tokens=True)

            for (orig_idx, _), trans in zip(batch_items, translated):
                translations[orig_idx] = trans

        return translations


class GoogleTranslator:
    """Google翻译（免费，通过网页接口）"""

    def __init__(self):
        self.api_url = "https://translate.googleapis.com/translate_a/single"
        self.call_count = 0

    def test_connection(self) -> str:
        """测试连接"""
        try:
            result = self.translate_single("Hello")
            return result
        except Exception as e:
            return f"[连接失败: {str(e)}]"

    def translate_single(self, text: str) -> str:
        if not text.strip():
            return ""

        params = {
            "client": "gtx",
            "sl": "en",
            "tl": "zh-CN",
            "dt": "t",
            "q": text,
        }

        try:
            response = requests.get(self.api_url, params=params, timeout=10)
            result = response.json()
            if result and len(result) > 0 and len(result[0]) > 0:
                translated = "".join([item[0] for item in result[0] if item[0]])
                return translated
            return "[翻译失败]"
        except Exception as e:
            return f"[错误: {str(e)}]"

    def translate_batch(self, texts: List[str], batch_size: int = 10) -> List[str]:
        total = len(texts)
        translations = [""] * total

        # 过滤有效文本
        valid_items = []
        for i, text in enumerate(texts):
            stripped = text.strip()
            if stripped and len(stripped) > 1 and not stripped.isdigit():
                valid_items.append((i, stripped))

        # 批量翻译（合并文本以减少请求）
        batch_texts = []
        batch_indices = []

        for idx, (orig_idx, text) in enumerate(valid_items):
            batch_texts.append(text)
            batch_indices.append(orig_idx)

            # 每10条或最后一条时发送请求
            if len(batch_texts) >= batch_size or idx == len(valid_items) - 1:
                combined = "\n".join(batch_texts)
                params = {
                    "client": "gtx",
                    "sl": "en",
                    "tl": "zh-CN",
                    "dt": "t",
                    "q": combined,
                }

                try:
                    response = requests.get(self.api_url, params=params, timeout=15)
                    result = response.json()

                    if result and len(result) > 0 and len(result[0]) > 0:
                        translated_parts = [item[0] for item in result[0] if item[0]]
                        # 按行分割翻译结果
                        if len(translated_parts) == len(batch_texts):
                            for i, trans in enumerate(translated_parts):
                                translations[batch_indices[i]] = trans
                        else:
                            # 如果分割失败，整体分配
                            combined_trans = "".join(translated_parts)
                            for i, orig_idx in enumerate(batch_indices):
                                translations[orig_idx] = combined_trans

                    time.sleep(0.5)  # 避免请求过快

                except Exception as e:
                    for orig_idx in batch_indices:
                        translations[orig_idx] = "[网络错误]"

                batch_texts = []
                batch_indices = []

        return translations


def create_translator(translator_type: str = "google", **kwargs):
    """创建翻译器工厂方法"""
    if translator_type == "baidu":
        return BaiduTranslator(
            app_id=kwargs.get("app_id", ""),
            secret_key=kwargs.get("secret_key", ""),
        )
    elif translator_type == "local":
        return LocalTranslator(
            model_name=kwargs.get("model_name", "Helsinki-NLP/opus-mt-en-zh"),
        )
    elif translator_type == "google":
        return GoogleTranslator()
    else:
        raise ValueError(f"不支持的翻译器类型: {translator_type}")
