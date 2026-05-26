import fitz
import os
from typing import List
from .pdf_reader import TextBlock


class PDFWriter:
    def __init__(self, original_doc: fitz.Document, font_path: str):
        self.doc = original_doc
        self.font_path = font_path
        self._font = None
        self._init_font()

    def _init_font(self):
        """初始化字体"""
        # 优先使用内置CJK字体
        try:
            self._font = fitz.Font("china-s")
        except Exception as e:
            print(f"内置字体加载失败: {e}")
            self._font = fitz.Font("helv")

    def replace_text_on_page(
        self, page_num: int, original_blocks: List[TextBlock], translated_texts: List[str]
    ):
        """替换页面中的文本"""
        page = self.doc[page_num]

        # 收集所有需要删除的文本区域
        rects = []
        text_items = []
        text_idx = 0

        for block in original_blocks:
            for span in block.spans:
                if text_idx < len(translated_texts):
                    translated = translated_texts[text_idx]
                    if translated and not translated.startswith("["):
                        rects.append(fitz.Rect(span.bbox))
                        text_items.append({
                            "origin": span.origin,
                            "text": translated,
                            "size": span.size,
                            "color": span.color,
                            "bbox": span.bbox,
                        })
                text_idx += 1

        # 使用redaction删除原始文本
        for rect in rects:
            page.add_redact_annot(rect, fill=(1, 1, 1))
        page.apply_redactions(images=fitz.PDF_REDACT_IMAGE_NONE)

        # 使用TextWriter写入翻译后的文本
        tw = fitz.TextWriter(page.rect)
        for item in text_items:
            text = item["text"]
            size = item["size"]
            color = item["color"]
            origin = item["origin"]

            # 转换颜色
            r = ((color >> 16) & 0xFF) / 255.0
            g = ((color >> 8) & 0xFF) / 255.0
            b = (color & 0xFF) / 255.0

            # 添加到TextWriter
            tw.append(origin, text, font=self._font, fontsize=size)

        # 写入到页面
        tw.write_text(page)

    def save(self, output_path: str):
        """保存PDF"""
        self.doc.save(output_path, garbage=4, deflate=True)

    def close(self):
        """关闭文档"""
        if self.doc:
            self.doc.close()
            self.doc = None
