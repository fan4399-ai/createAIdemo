"""导出工具：将 Markdown 报告转换为 Word / Markdown 文件下载"""
import io
import re

from docx import Document
from docx.shared import Pt, RGBColor


# 行内格式 token：加粗 / 行内代码 / 链接 / 斜体
_INLINE_RE = re.compile(
    r"\*\*(.+?)\*\*"                # **bold**
    r"|`([^`]+?)`"                 # `code`
    r"|\[([^\]]+)\]\(([^)]+)\)"    # [text](url)
    r"|\*(.+?)\*"                  # *italic*
)


def export_to_word(markdown_text: str, title: str = "报告") -> bytes:
    """将 Markdown 内容转换为格式化的 Word 文档（.docx）。

    支持：标题 H1-H4、加粗、斜体、行内代码、链接、有序/无序列表、
    引用、分隔线、代码块与普通段落。
    """
    doc = Document()

    style = doc.styles["Normal"]
    style.font.name = "Microsoft YaHei"
    style.font.size = Pt(10.5)
    style.paragraph_format.space_after = Pt(6)
    style.paragraph_format.line_spacing = 1.5

    lines = markdown_text.split("\n")
    in_code_block = False

    for line in lines:
        stripped = line.strip()

        # 代码块（围栏 ```）
        if stripped.startswith("```"):
            in_code_block = not in_code_block
            continue
        if in_code_block:
            p = doc.add_paragraph(line)
            for run in p.runs:
                run.font.name = "Consolas"
                run.font.size = Pt(9)
            continue

        # 空行
        if not stripped:
            continue

        # 分隔线
        if stripped.startswith("---") or stripped.startswith("***"):
            doc.add_paragraph("─" * 40)
            continue

        # 标题
        m = re.match(r"^(#{1,4})\s+(.*)$", stripped)
        if m:
            level = len(m.group(1))
            p = doc.add_heading(m.group(2), level=level)
            _set_heading_font(p, Pt(20 - 2 * level))
            continue

        # 引用
        if stripped.startswith(">"):
            p = doc.add_paragraph()
            p.paragraph_format.left_indent = Pt(16)
            _add_inline(p, stripped.lstrip("> ").strip())
            for r in p.runs:
                r.font.italic = True
                r.font.color.rgb = RGBColor(0x55, 0x55, 0x55)
            continue

        # 无序列表
        if stripped.startswith("- ") or stripped.startswith("* "):
            p = doc.add_paragraph(style="List Bullet")
            _add_inline(p, stripped[2:].strip())
            continue

        # 有序列表
        om = re.match(r"^\d+\.\s+(.*)$", stripped)
        if om:
            p = doc.add_paragraph(style="List Number")
            _add_inline(p, om.group(1).strip())
            continue

        # 普通段落
        p = doc.add_paragraph()
        _add_inline(p, stripped)

    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer.getvalue()


def _set_heading_font(paragraph, size: Pt):
    for run in paragraph.runs:
        run.font.name = "Microsoft YaHei"
        run.font.size = size
        run.font.color.rgb = RGBColor(0x1A, 0x1A, 0x1A)


def _add_inline(paragraph, text: str):
    """解析行内格式（加粗/斜体/代码/链接）并写入段落。"""
    pos = 0
    for m in _INLINE_RE.finditer(text):
        if m.start() > pos:
            paragraph.add_run(text[pos : m.start()])
        if m.group(1) is not None:
            r = paragraph.add_run(m.group(1))
            r.bold = True
        elif m.group(2) is not None:
            r = paragraph.add_run(m.group(2))
            r.font.name = "Consolas"
            r.font.size = Pt(9)
        elif m.group(3) is not None:
            paragraph.add_run(m.group(3))
            url = m.group(4)
            if url and not url.lower().startswith(("javascript:", "data:")):
                note = paragraph.add_run(f" ({url})")
                note.font.size = Pt(9)
                note.font.color.rgb = RGBColor(0x55, 0x55, 0x55)
        elif m.group(5) is not None:
            r = paragraph.add_run(m.group(5))
            r.italic = True
        pos = m.end()
    if pos < len(text):
        paragraph.add_run(text[pos:])
