import fitz
from dataclasses import dataclass
from typing import List, Tuple


@dataclass
class TextSpan:
    """文本片段"""
    text: str
    bbox: Tuple[float, float, float, float]
    origin: Tuple[float, float]
    font: str
    size: float
    color: int
    flags: int


@dataclass
class TextBlock:
    """文本块"""
    spans: List[TextSpan]
    block_no: int


class PDFReader:
    def __init__(self, pdf_path: str):
        self.doc = fitz.open(pdf_path)
        self._is_scanned = None

    def is_scanned_pdf(self, page_num: int = 0) -> bool:
        """检测是否为扫描版PDF"""
        if self._is_scanned is not None:
            return self._is_scanned

        page = self.doc[min(page_num, len(self.doc) - 1)]
        text = page.get_text().strip()
        images = page.get_images()

        # 如果没有文本但有图片，可能是扫描版
        if len(text) < 50 and len(images) > 0:
            self._is_scanned = True
        else:
            self._is_scanned = False

        return self._is_scanned

    def extract_page_blocks(self, page_num: int) -> List[TextBlock]:
        """提取页面文本块及其格式信息"""
        page = self.doc[page_num]
        blocks = page.get_text("dict", flags=fitz.TEXT_PRESERVE_WHITESPACE)["blocks"]

        result = []
        for block in blocks:
            if block["type"] == 0:  # 文本块
                spans = []
                for line in block["lines"]:
                    for span in line["spans"]:
                        text = span["text"].strip()
                        if text:
                            spans.append(TextSpan(
                                text=text,
                                bbox=span["bbox"],
                                origin=span["origin"],
                                font=span["font"],
                                size=span["size"],
                                color=span["color"],
                                flags=span["flags"],
                            ))
                if spans:
                    result.append(TextBlock(
                        spans=spans,
                        block_no=block["number"],
                    ))
        return result

    def get_page_image(self, page_num: int) -> bytes:
        """获取页面图片（用于OCR）"""
        page = self.doc[page_num]
        pix = page.get_pixmap(dpi=200)
        return pix.tobytes("png")

    def get_page_count(self) -> int:
        return len(self.doc)

    def close(self):
        if self.doc:
            self.doc.close()
            self.doc = None
