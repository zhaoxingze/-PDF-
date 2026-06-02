import fitz
import os
from typing import List
from .pdf_reader import TextBlock


class PDFWriter:
    def __init__(self, original_doc: fitz.Document, font_path: str):
        self.doc = original_doc
        self.font_path = font_path
        self._font_name = "notosanssc"
        self._font_file = font_path if font_path and os.path.exists(font_path) else None
        self._init_font()

    def _init_font(self):
        """初始化字体"""
        if self._font_file:
            return
        self._font_name = "china-s"

    def replace_text_on_page(
        self, page_num: int, original_blocks: List[TextBlock], translated_texts: List[str]
    ):
        """替换页面中的文本（按block级别替换）"""
        page = self.doc[page_num]

        # 收集需要替换的block信息
        replace_items = []
        for i, block in enumerate(original_blocks):
            if i < len(translated_texts):
                translated = translated_texts[i]
                if translated and not translated.startswith("["):
                    # 取第一个span的字号和颜色作为block的样式
                    first_span = block.spans[0]
                    replace_items.append({
                        "bbox": block.block_bbox,
                        "text": translated,
                        "size": first_span.size,
                        "color": first_span.color,
                    })

        if not replace_items:
            return

        # 使用redaction删除原始文本
        for item in replace_items:
            page.add_redact_annot(fitz.Rect(item["bbox"]), fill=(1, 1, 1))
        page.apply_redactions(images=fitz.PDF_REDACT_IMAGE_NONE)

        # 使用insert_textbox写入翻译后的文本（自动换行）
        for item in replace_items:
            x0, y0, x1, y1 = item["bbox"]
            size = item["size"]
            color = item["color"]

            # 稍微扩大文本框以容纳翻译后的文字
            text_rect = fitz.Rect(x0, y0, x1, y1)

            r = ((color >> 16) & 0xFF) / 255.0
            g = ((color >> 8) & 0xFF) / 255.0
            b = (color & 0xFF) / 255.0

            self._insert_textbox_fitting(
                page,
                text_rect,
                item["text"],
                fontsize=size,
                color=(r, g, b),
            )

    def _insert_textbox_fitting(self, page, rect, text, fontsize, color):
        min_size = max(4.0, fontsize * 0.55)
        current_size = fontsize
        fontfile = self._font_file

        while current_size >= min_size:
            remaining = page.insert_textbox(
                rect,
                text,
                fontname=self._font_name,
                fontfile=fontfile,
                fontsize=current_size,
                color=color,
                align=fitz.TEXT_ALIGN_LEFT,
            )
            if remaining >= 0:
                return
            current_size -= 0.5

        expanded = fitz.Rect(
            rect.x0,
            rect.y0,
            rect.x1,
            min(page.rect.height, rect.y1 + fontsize * 3),
        )
        page.insert_textbox(
            expanded,
            text,
            fontname=self._font_name,
            fontfile=fontfile,
            fontsize=min_size,
            color=color,
            align=fitz.TEXT_ALIGN_LEFT,
        )

    def save(self, output_path: str):
        """保存PDF"""
        self.doc.save(output_path, garbage=4, deflate=True)

    def close(self):
        """关闭文档"""
        if self.doc:
            self.doc.close()
            self.doc = None
