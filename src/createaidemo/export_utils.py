"""
导出工具：将 Markdown 报告转换为 Word / Markdown 文件下载
"""
import io
import re

from docx import Document
from docx.shared import Pt, Inches, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH


def export_to_word(markdown_text: str, title: str = "报告") -> bytes:
    """
    将 Markdown 内容转换为格式化的 Word 文档（.docx）
    支持：标题 H1-H3、加粗、列表、分隔线、普通段落
    """
    doc = Document()

    # 设置默认字体
    style = doc.styles["Normal"]
    style.font.name = "Microsoft YaHei"
    style.font.size = Pt(10.5)
    style.paragraph_format.space_after = Pt(6)
    style.paragraph_format.line_spacing = 1.5

    lines = markdown_text.split("\n")
    in_code_block = False

    for line in lines:
        stripped = line.strip()

        # 代码块处理
        if stripped.startswith("```"):
            in_code_block = not in_code_block
            continue
        if in_code_block:
            p = doc.add_paragraph(line)
            p.style = doc.styles["Normal"]
            run = p.runs[0] if p.runs else p.add_run(line)
            run.font.name = "Consolas"
            run.font.size = Pt(9)
            continue

        # 空行
        if not stripped:
            doc.add_paragraph("")
            continue

        # 分隔线
        if stripped.startswith("---") or stripped.startswith("***"):
            doc.add_paragraph("─" * 60)
            continue

        # 标题
        if stripped.startswith("# "):
            p = doc.add_heading(stripped[2:], level=1)
            _set_heading_font(p, Pt(18))
        elif stripped.startswith("## "):
            p = doc.add_heading(stripped[3:], level=2)
            _set_heading_font(p, Pt(14))
        elif stripped.startswith("### "):
            p = doc.add_heading(stripped[4:], level=3)
            _set_heading_font(p, Pt(12))
        elif stripped.startswith("#### "):
            p = doc.add_heading(stripped[5:], level=4)
            _set_heading_font(p, Pt(11))

        # 无序列表
        elif stripped.startswith("- ") or stripped.startswith("* "):
            doc.add_paragraph(_strip_markdown_bold(stripped[2:]), style="List Bullet")

        # 有序列表
        elif re.match(r"^\d+\.\s", stripped):
            content = re.sub(r"^\d+\.\s", "", stripped)
            doc.add_paragraph(_strip_markdown_bold(content), style="List Number")

        # 普通段落
        else:
            p = doc.add_paragraph()
            _add_formatted_run(p, _strip_markdown_bold(stripped))

    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer.getvalue()


def _set_heading_font(paragraph, size: Pt):
    """统一设置标题字体"""
    for run in paragraph.runs:
        run.font.name = "Microsoft YaHei"
        run.font.size = size
        run.font.color.rgb = RGBColor(0x1A, 0x1A, 0x1A)


def _strip_markdown_bold(text: str) -> str:
    """去掉 Markdown 加粗标记 ** **"""
    return re.sub(r"\*\*(.+?)\*\*", r"\1", text)


def _add_formatted_run(paragraph, text: str):
    """手动解析加粗并添加到段落"""
    parts = re.split(r"(\*\*.+?\*\*)", text)
    for part in parts:
        if part.startswith("**") and part.endswith("**"):
            run = paragraph.add_run(part[2:-2])
            run.bold = True
        else:
            paragraph.add_run(part)
