from dataclasses import dataclass
from typing import List, Optional, Tuple
from docx import Document
from docx.document import Document as DocumentType
from docx.oxml.table import CT_Tbl
from docx.oxml.text.paragraph import CT_P
from docx.table import Table, _Cell
from docx.text.paragraph import Paragraph


@dataclass
class DocxParagraph:
    """Word文档段落"""
    text: str
    index: int
    style_name: str = ""
    font_name: Optional[str] = None
    font_size: Optional[float] = None
    bold: Optional[bool] = None
    italic: Optional[bool] = None
    color_rgb: Optional[str] = None  # hex string like "000000"


class DocxReader:
    def __init__(self, docx_path: str):
        self.doc = Document(docx_path)
        self.path = docx_path

    def extract_paragraphs(self) -> List[DocxParagraph]:
        """提取所有非空段落及其格式信息"""
        result = []
        for i, para in enumerate(iter_document_paragraphs(self.doc)):
            text = para.text.strip()
            if not text:
                continue

            # 段落样式
            style_name = para.style.name if para.style else ""

            # 从runs中提取主要格式（多数vote）
            font_name, font_size, bold, italic, color_rgb = self._dominant_format(para)

            result.append(DocxParagraph(
                text=text,
                index=i,
                style_name=style_name,
                font_name=font_name,
                font_size=font_size,
                bold=bold,
                italic=italic,
                color_rgb=color_rgb,
            ))

        return result

    def _dominant_format(self, para) -> Tuple[Optional[str], Optional[float], Optional[bool], Optional[bool], Optional[str]]:
        """从段落的runs中提取主要格式"""
        runs = para.runs
        if not runs:
            return None, None, None, None, None

        # 统计各格式出现的频率（按字符数加权）
        name_count = {}
        size_count = {}
        bold_true = 0
        bold_false = 0
        italic_true = 0
        italic_false = 0
        color_count = {}

        for run in runs:
            char_count = len(run.text)
            if char_count == 0:
                continue

            if run.font.name:
                name_count[run.font.name] = name_count.get(run.font.name, 0) + char_count
            if run.font.size:
                size_pt = run.font.size.pt
                size_count[size_pt] = size_count.get(size_pt, 0) + char_count
            if run.bold:
                bold_true += char_count
            else:
                bold_false += char_count
            if run.italic:
                italic_true += char_count
            else:
                italic_false += char_count
            if run.font.color and run.font.color.rgb:
                hex_color = str(run.font.color.rgb)
                color_count[hex_color] = color_count.get(hex_color, 0) + char_count

        def most_common(d):
            if not d:
                return None
            return max(d, key=d.get)

        font_name = most_common(name_count)
        font_size = most_common(size_count)
        bold = bold_true > bold_false if (bold_true + bold_false) > 0 else None
        italic = italic_true > italic_false if (italic_true + italic_false) > 0 else None
        color_rgb = most_common(color_count)

        return font_name, font_size, bold, italic, color_rgb

    def close(self):
        pass


def iter_document_paragraphs(doc):
    yield from _iter_block_paragraphs(doc)

    for section in doc.sections:
        yield from _iter_block_paragraphs(section.header)
        yield from _iter_block_paragraphs(section.footer)


def _iter_block_paragraphs(parent):
    if isinstance(parent, DocumentType):
        parent_element = parent.element.body
    elif isinstance(parent, _Cell):
        parent_element = parent._tc
    else:
        parent_element = parent._element

    for child in parent_element.iterchildren():
        if isinstance(child, CT_P):
            yield Paragraph(child, parent)
        elif isinstance(child, CT_Tbl):
            table = Table(child, parent)
            for row in table.rows:
                for cell in row.cells:
                    yield from _iter_block_paragraphs(cell)
