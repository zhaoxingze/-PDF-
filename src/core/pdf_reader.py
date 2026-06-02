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
    merged_text: str = ""
    block_bbox: Tuple[float, float, float, float] = (0, 0, 0, 0)


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
        seen_spans = set()
        for block in blocks:
            if block["type"] == 0:  # 文本块
                spans = []
                for line in block["lines"]:
                    for span in sorted(line["spans"], key=lambda item: item["bbox"][0]):
                        text = span["text"].strip()
                        key = (text, self._rounded_bbox(span["bbox"]))
                        if text and key not in seen_spans:
                            seen_spans.add(key)
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
                    merged = self._merge_spans_by_line(spans)
                    # 计算整个block的包围框
                    x0 = min(s.bbox[0] for s in spans)
                    y0 = min(s.bbox[1] for s in spans)
                    x1 = max(s.bbox[2] for s in spans)
                    y1 = max(s.bbox[3] for s in spans)
                    result.append(TextBlock(
                        spans=spans,
                        block_no=block["number"],
                        merged_text=merged,
                        block_bbox=(x0, y0, x1, y1),
                    ))
        return sorted(result, key=lambda item: (round(item.block_bbox[1], 1), round(item.block_bbox[0], 1), item.block_no))

    @staticmethod
    def _rounded_bbox(bbox: Tuple[float, float, float, float]) -> Tuple[int, int, int, int]:
        return tuple(round(value * 10) for value in bbox)

    @staticmethod
    def _merge_spans_by_line(spans: List[TextSpan]) -> str:
        lines = []
        for span in sorted(spans, key=lambda item: (round(item.bbox[1] / 3), item.bbox[0])):
            if not lines or abs(lines[-1][0] - span.bbox[1]) > max(2.0, span.size * 0.35):
                lines.append((span.bbox[1], [span]))
            else:
                lines[-1][1].append(span)

        merged_lines = []
        for _, line_spans in lines:
            ordered = sorted(line_spans, key=lambda item: item.bbox[0])
            merged_lines.append(" ".join(span.text for span in ordered if span.text))
        return "\n".join(line for line in merged_lines if line)

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
