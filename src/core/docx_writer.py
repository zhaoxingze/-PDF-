from typing import List
from docx import Document
from docx.shared import Pt, RGBColor
from docx.oxml.ns import qn
from .docx_reader import DocxParagraph, iter_document_paragraphs


class DocxWriter:
    def __init__(self, original_path: str):
        self.doc = Document(original_path)
        self.path = original_path

    def replace_paragraphs(self, paragraphs: List[DocxParagraph], translated_texts: List[str]):
        """替换段落文本，保留格式"""
        doc_paragraphs = list(iter_document_paragraphs(self.doc))
        for para_info, translated in zip(paragraphs, translated_texts):
            if not translated or translated.startswith("["):
                continue

            if para_info.index >= len(doc_paragraphs):
                continue

            para = doc_paragraphs[para_info.index]

            # 清除所有runs
            for run in para.runs:
                run._element.getparent().remove(run._element)

            new_run = para.add_run(translated)

            # 应用原始格式
            font_name = para_info.font_name or "Microsoft YaHei"
            if font_name:
                new_run.font.name = font_name
                # 设置东亚字体
                r = new_run._element
                rPr = r.get_or_add_rPr()
                rFonts = rPr.find(qn('w:rFonts'))
                if rFonts is None:
                    rFonts = r.makeelement(qn('w:rFonts'), {})
                    rPr.insert(0, rFonts)
                rFonts.set(qn('w:eastAsia'), font_name)

            if para_info.font_size:
                new_run.font.size = Pt(para_info.font_size)
            if para_info.bold is not None:
                new_run.font.bold = para_info.bold
            if para_info.italic is not None:
                new_run.font.italic = para_info.italic
            if para_info.color_rgb:
                try:
                    new_run.font.color.rgb = RGBColor.from_string(para_info.color_rgb)
                except Exception:
                    pass

    def save(self, output_path: str):
        """保存文档"""
        self.doc.save(output_path)

    def close(self):
        pass
