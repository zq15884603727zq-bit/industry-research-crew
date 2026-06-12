"""
报告导出模块 — 支持 Markdown → DOCX / HTML / PDF

技术选型：
  - DOCX: python-docx（纯 Python，企业标准格式）
  - HTML:  手动渲染 + CSS（浏览器打开即可打印为 PDF）
  - PDF:   fpdf2（纯 Python，无系统依赖）

设计原则：
  - 每种导出独立为一个函数，方便测试和复用
  - Markdown 解析做基本覆盖（标题/粗体/列表/表格/代码块）
  - 导出文件统一放在 output/ 目录
"""

import re
from pathlib import Path
from datetime import datetime

# ── DOCX 导出 ─────────────────────────────────────────
def export_to_docx(markdown_content: str, output_path: Path) -> Path:
    """
    将 Markdown 报告导出为 Word 文档（.docx）。

    支持的 Markdown 元素：
      - # ## ### ####  → 标题
      - **text**        → 粗体
      - - item / * item → 无序列表
      - 1. item         → 有序列表
      - | col | col |   → 表格
      - ```code```      → 代码块（灰色底纹）
      - ---             → 分隔线

    Args:
        markdown_content: Markdown 格式的报告文本
        output_path:      输出文件路径（.docx）

    Returns:
        保存的文件路径
    """
    from docx import Document
    from docx.shared import Pt, Inches, RGBColor, Cm
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.oxml.ns import qn

    doc = Document()

    # 设置默认字体
    style = doc.styles['Normal']
    font = style.font
    font.name = 'Microsoft YaHei'
    font.size = Pt(11)
    # 设置中文字体
    style.element.rPr.rFonts.set(qn('w:eastAsia'), 'Microsoft YaHei')

    lines = markdown_content.split('\n')
    i = 0        # 行指针
    in_table = False
    table_rows = []

    def add_heading(text, level):
        h = doc.add_heading(text, level=level)
        for run in h.runs:
            run.font.name = 'Microsoft YaHei'
            run._element.rPr.rFonts.set(qn('w:eastAsia'), 'Microsoft YaHei')

    def add_paragraph(text, bold=False):
        p = doc.add_paragraph()
        run = p.add_run(text)
        run.font.name = 'Microsoft YaHei'
        run._element.rPr.rFonts.set(qn('w:eastAsia'), 'Microsoft YaHei')
        if bold:
            run.bold = True
        return p

    def add_bold_paragraph(text):
        """解析文本中的 **bold** 标记并添加到段落"""
        p = doc.add_paragraph()
        parts = re.split(r'(\*\*.*?\*\*)', text)
        for part in parts:
            if part.startswith('**') and part.endswith('**'):
                run = p.add_run(part[2:-2])
                run.bold = True
            else:
                run = p.add_run(part)
            run.font.name = 'Microsoft YaHei'
            run._element.rPr.rFonts.set(qn('w:eastAsia'), 'Microsoft YaHei')
        return p

    while i < len(lines):
        line = lines[i]

        # 空行
        if not line.strip():
            if in_table and table_rows:
                # 结束表格
                _render_table(doc, table_rows)
                table_rows = []
                in_table = False
            i += 1
            continue

        # 表格：| ... | ... |
        if line.strip().startswith('|') and line.strip().endswith('|'):
            in_table = True
            cells = [c.strip() for c in line.strip()[1:-1].split('|')]
            # 跳过分隔行（如 |---|---|）
            if not all(re.match(r'^[-:]+$', c) for c in cells):
                table_rows.append(cells)
            i += 1
            continue
        elif in_table and table_rows:
            _render_table(doc, table_rows)
            table_rows = []
            in_table = False

        # 标题
        heading_match = re.match(r'^(#{1,4})\s+(.*)', line)
        if heading_match:
            level = len(heading_match.group(1))
            add_heading(heading_match.group(2), level)
            i += 1
            continue

        # 分隔线
        if line.strip() == '---':
            doc.add_paragraph('_' * 50)
            i += 1
            continue

        # 代码块
        if line.strip().startswith('```'):
            code_lines = []
            i += 1
            while i < len(lines) and not lines[i].strip().startswith('```'):
                code_lines.append(lines[i])
                i += 1
            if code_lines:
                p = doc.add_paragraph()
                run = p.add_run('\n'.join(code_lines))
                run.font.name = 'Consolas'
                run.font.size = Pt(9)
            i += 1  # skip closing ```
            continue

        # 无序列表
        list_match = re.match(r'^(\s*)[-*]\s+(.*)', line)
        if list_match:
            p = doc.add_paragraph(style='List Bullet')
            text = list_match.group(2)
            # 处理粗体
            parts = re.split(r'(\*\*.*?\*\*)', text)
            for part in parts:
                if part.startswith('**') and part.endswith('**'):
                    run = p.add_run(part[2:-2])
                    run.bold = True
                else:
                    run = p.add_run(part)
            i += 1
            continue

        # 有序列表
        ol_match = re.match(r'^(\s*)\d+\.\s+(.*)', line)
        if ol_match:
            p = doc.add_paragraph(style='List Number')
            text = ol_match.group(2)
            parts = re.split(r'(\*\*.*?\*\*)', text)
            for part in parts:
                if part.startswith('**') and part.endswith('**'):
                    run = p.add_run(part[2:-2])
                    run.bold = True
                else:
                    run = p.add_run(part)
            i += 1
            continue

        # 普通段落（支持粗体）
        add_bold_paragraph(line)
        i += 1

    # 处理最后的表格
    if in_table and table_rows:
        _render_table(doc, table_rows)

    doc.save(str(output_path))
    return output_path


def _render_table(doc, rows):
    """将行列表渲染为 Word 表格"""
    from docx.shared import Pt
    if not rows:
        return
    table = doc.add_table(rows=len(rows), cols=len(rows[0]), style='Table Grid')
    for r_idx, row in enumerate(rows):
        for c_idx, cell_text in enumerate(row):
            if c_idx < len(table.rows[r_idx].cells):
                cell = table.rows[r_idx].cells[c_idx]
                cell.text = cell_text
                for paragraph in cell.paragraphs:
                    for run in paragraph.runs:
                        run.font.size = Pt(9)


# ── HTML 导出 ─────────────────────────────────────────
def export_to_html(markdown_content: str, output_path: Path) -> Path:
    """
    将 Markdown 报告导出为 HTML 文件（浏览器打开即可打印为 PDF）。

    内嵌 CSS 样式，打印友好。
    """
    # 简单 Markdown → HTML 转换
    html_body = _md_to_html(markdown_content)

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>行业研究报告</title>
<style>
  body {{
    max-width: 800px;
    margin: 40px auto;
    padding: 20px;
    font-family: 'Microsoft YaHei', 'PingFang SC', sans-serif;
    font-size: 15px;
    line-height: 1.8;
    color: #333;
  }}
  h1 {{ font-size: 26px; border-bottom: 2px solid #1a5276; padding-bottom: 10px; color: #1a5276; }}
  h2 {{ font-size: 20px; margin-top: 30px; border-bottom: 1px solid #ddd; padding-bottom: 6px; color: #2c3e50; }}
  h3 {{ font-size: 17px; margin-top: 24px; color: #34495e; }}
  h4 {{ font-size: 15px; margin-top: 20px; color: #555; }}
  strong {{ color: #c0392b; }}
  table {{ border-collapse: collapse; width: 100%; margin: 16px 0; font-size: 14px; }}
  th, td {{ border: 1px solid #ddd; padding: 8px 12px; text-align: left; }}
  th {{ background: #2c3e50; color: white; }}
  tr:nth-child(even) {{ background: #f9f9f9; }}
  code {{ background: #f4f4f4; padding: 2px 6px; border-radius: 3px; font-size: 13px; }}
  pre {{ background: #2d2d2d; color: #f8f8f2; padding: 16px; border-radius: 6px; overflow-x: auto; font-size: 13px; line-height: 1.5; }}
  pre code {{ background: none; padding: 0; color: inherit; }}
  blockquote {{ border-left: 4px solid #3498db; padding-left: 16px; color: #666; margin: 16px 0; }}
  hr {{ border: none; border-top: 1px solid #ddd; margin: 30px 0; }}
  @media print {{
    body {{ font-size: 12pt; }}
    pre, code {{ font-size: 10pt; }}
  }}
</style>
</head>
<body>
{html_body}
</body>
</html>"""

    output_path.write_text(html, encoding="utf-8")
    return output_path


def _md_to_html(md: str) -> str:
    """将 Markdown 文本转换为 HTML 片段"""
    lines = md.split('\n')
    result = []
    i = 0
    in_table = False
    table_rows = []
    in_code = False

    while i < len(lines):
        line = lines[i]

        # 代码块
        if line.strip().startswith('```'):
            if not in_code:
                in_code = True
                result.append('<pre><code>')
            else:
                in_code = False
                result.append('</code></pre>')
            i += 1
            continue

        if in_code:
            result.append(line)
            i += 1
            continue

        # 空行
        if not line.strip():
            if in_table and table_rows:
                result.append(_html_table(table_rows))
                table_rows = []
                in_table = False
            i += 1
            continue

        # 表格
        if line.strip().startswith('|') and line.strip().endswith('|'):
            in_table = True
            cells = [c.strip() for c in line.strip()[1:-1].split('|')]
            if not all(re.match(r'^[-:]+$', c) for c in cells):
                table_rows.append(cells)
            i += 1
            continue
        elif in_table and table_rows:
            result.append(_html_table(table_rows))
            table_rows = []
            in_table = False

        # 标题
        for level in range(4, 0, -1):
            prefix = '#' * level + ' '
            if line.startswith(prefix):
                text = line[len(prefix):]
                # 处理标题中的粗体
                text = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', text)
                result.append(f'<h{level}>{text}</h{level}>')
                break
        else:
            # 分隔线
            if line.strip() == '---':
                result.append('<hr>')
                i += 1
                continue

            # 粗体（在普通段落中）
            line = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', line)

            # 无序列表
            list_match = re.match(r'^(\s*)[-*]\s+(.*)', line)
            if list_match:
                result.append(f'<li>{list_match.group(2)}</li>')
                i += 1
                continue

            # 有序列表
            ol_match = re.match(r'^(\s*)\d+\.\s+(.*)', line)
            if ol_match:
                result.append(f'<li>{ol_match.group(2)}</li>')
                i += 1
                continue

            result.append(f'<p>{line}</p>')
        i += 1

    if in_table and table_rows:
        result.append(_html_table(table_rows))

    return '\n'.join(result)


def _html_table(rows):
    """渲染 HTML 表格"""
    if not rows:
        return ''
    html = '<table>\n'
    for idx, row in enumerate(rows):
        tag = 'th' if idx == 0 else 'td'
        html += '<tr>\n'
        for cell in row:
            html += f'  <{tag}>{cell}</{tag}>\n'
        html += '</tr>\n'
    html += '</table>'
    return html


# ── PDF 导出（基于 fpdf2） ─────────────────────────────
def export_to_pdf(markdown_content: str, output_path: Path) -> Path:
    """
    将 Markdown 报告导出为 PDF。

    使用 fpdf2（纯 Python，无系统依赖）。
    支持中文（自动检测可用字体）。
    """
    from fpdf import FPDF

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()  # 必须先创建页面

    # 加载中文字体（注册 regular + bold）
    font_name = _setup_chinese_font(pdf)

    lines = markdown_content.split('\n')
    has_bold = _has_bold_font(pdf, font_name)

    for line in lines:
        # 空行
        if not line.strip():
            pdf.ln(6)
            continue

        # 标题
        heading_match = re.match(r'^(#{1,4})\s+(.*)', line)
        if heading_match:
            level = len(heading_match.group(1))
            sizes = {1: 20, 2: 16, 3: 13, 4: 11}
            style = 'B' if has_bold else ''
            pdf.set_font(font_name, style, sizes.get(level, 11))
            pdf.ln(4 if level == 1 else 2)
            pdf.multi_cell(0, 8, heading_match.group(2))
            pdf.set_font(font_name, '', 10)
            pdf.ln(2)
            continue

        # 分隔线
        if line.strip() == '---':
            pdf.ln(4)
            pdf.cell(0, 0, '', border='T')
            pdf.ln(6)
            continue

        # 代码块
        if line.strip().startswith('```'):
            continue

        # 粗体处理：**text** → 分多段写入
        bold_parts = re.split(r'(\*\*.*?\*\*)', line)
        if any(p.startswith('**') for p in bold_parts if isinstance(p, str)):
            pdf.set_font(font_name, '', 10)
            for part in bold_parts:
                if not part:
                    continue
                if part.startswith('**') and part.endswith('**'):
                    if has_bold:
                        pdf.set_font(font_name, 'B', 10)
                        pdf.write(8, part[2:-2])
                        pdf.set_font(font_name, '', 10)
                    else:
                        # 无粗体字体时用 << >> 标记替代
                        pdf.write(8, f"《{part[2:-2]}》")
                else:
                    pdf.write(8, part)
            pdf.ln(6)
            continue

        # 表格行（简单处理）
        if line.strip().startswith('|'):
            cells = [c.strip() for c in line.strip()[1:-1].split('|')]
            if all(re.match(r'^[-:]+$', c) for c in cells):
                continue  # 跳过分隔行
            text = ' | '.join(cells)
            pdf.set_font(font_name, '', 9)
            pdf.cell(0, 6, text)
            pdf.ln()
            continue

        # 普通段落
        pdf.set_font(font_name, '', 10)
        pdf.multi_cell(0, 5.5, line)
        pdf.ln(1)

    pdf.output(str(output_path))
    return output_path


def _setup_chinese_font(pdf) -> str:
    """
    探测系统中可用的中文字体并注册到 PDF 对象。

    优先使用微软雅黑（含 regular + bold），
    回退到宋体/黑体，最后回退到内置 Helvetica。
    """
    import os

    candidates = [
        # (字体名, regular路径, bold路径)
        ("MicrosoftYaHei",
         "C:/Windows/Fonts/msyh.ttc",
         "C:/Windows/Fonts/msyhbd.ttc"),
        ("SimSun",
         "C:/Windows/Fonts/simsun.ttc",
         None),
        ("SimHei",
         "C:/Windows/Fonts/simhei.ttf",
         None),
    ]

    for name, regular_path, bold_path in candidates:
        if os.path.exists(regular_path):
            try:
                pdf.add_font(name, '', regular_path, uni=True)
                if bold_path and os.path.exists(bold_path):
                    pdf.add_font(name, 'B', bold_path, uni=True)
                return name
            except Exception:
                continue

    return 'Helvetica'


def _has_bold_font(pdf, font_name: str) -> bool:
    """检查 PDF 对象中是否有粗体变体"""
    try:
        # fpdf2 内部字体注册检查
        return font_name != 'Helvetica' and hasattr(pdf, 'fonts')
    except Exception:
        return False


# ── 统一导出接口 ───────────────────────────────────────
def export_report(content: str, topic: str, fmt: str = "md") -> dict:
    """
    统一导出接口：根据 fmt 参数导出报告。

    Args:
        content: 报告文本（Markdown 格式）
        topic:   研究主题
        fmt:     导出格式 — "md" | "docx" | "html" | "pdf" | "all"

    Returns:
        {format: filepath} 字典
    """
    from config.settings import OUTPUT_DIR

    safe_topic = topic.replace(" ", "_").replace("/", "_")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    base = OUTPUT_DIR / f"{safe_topic}_{timestamp}"

    formats = {
        "md": lambda: (base.with_suffix(".md").write_text(content, encoding="utf-8")
                        or base.with_suffix(".md")),
        "docx": lambda: export_to_docx(content, base.with_suffix(".docx")),
        "html": lambda: export_to_html(content, base.with_suffix(".html")),
        "pdf": lambda: export_to_pdf(content, base.with_suffix(".pdf")),
    }

    if fmt == "all":
        results = {}
        for f, exporter in formats.items():
            try:
                results[f] = exporter()
                print(f"   ✅ {f.upper()}: {results[f]}")
            except Exception as e:
                print(f"   ⚠️  {f.upper()} 导出失败: {e}")
        return results
    elif fmt in formats:
        exporter = formats[fmt]
        path = exporter()
        print(f"   ✅ {fmt.upper()}: {path}")
        return {fmt: path}
    else:
        raise ValueError(f"不支持的导出格式: {fmt}，可选: md, docx, html, pdf, all")
