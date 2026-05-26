import fitz
import os


class FontManager:
    def __init__(self, font_path: str):
        self.font_path = font_path
        self._font = None
        self._font_name = None

    def get_font(self) -> fitz.Font:
        """获取中文字体（懒加载）"""
        if self._font is None:
            if os.path.exists(self.font_path):
                try:
                    self._font = fitz.Font(fontfile=self.font_path)
                    self._font_name = "chinese"
                except Exception as e:
                    print(f"加载字体失败: {e}")
                    self._font = fitz.Font("helv")
                    self._font_name = "helv"
            else:
                self._font = fitz.Font("helv")
                self._font_name = "helv"
        return self._font

    def get_font_name(self) -> str:
        """获取字体名称"""
        if self._font_name is None:
            self.get_font()
        return self._font_name
