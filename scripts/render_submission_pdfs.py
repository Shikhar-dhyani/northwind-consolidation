"""Render the committed architecture/reflection Markdown and enforce page limits.

Optional dependency: python -m pip install -r requirements-docs.txt
"""

import hashlib
from html import escape
import json
from pathlib import Path
import re

from pypdf import PdfReader
from reportlab import Version
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.pdfgen import canvas
from reportlab.platypus import PageBreak, Paragraph, Preformatted, SimpleDocTemplate

ROOT = Path(__file__).resolve().parents[1]


def inline(text):
    text = escape(text)
    text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text)
    text = re.sub(r'`([^`]+)`', r'<font name="Courier" size="8.5">\1</font>', text)
    return text


def flow(text, styles):
    result, paragraph, code, in_code = [], [], [], False

    def flush():
        if paragraph:
            result.append(Paragraph(inline(' '.join(paragraph)), styles['body']))
            paragraph.clear()

    for line in text.splitlines():
        if line.startswith('```'):
            flush()
            if in_code:
                result.append(Preformatted('\n'.join(code), styles['code']))
                code.clear()
            in_code = not in_code
        elif in_code:
            code.append(line)
        elif line.startswith('# '):
            flush()
            result.append(Paragraph(inline(line[2:]), styles['title']))
        elif line.startswith('## '):
            flush()
            label = re.sub(r'^Page \d of \d - ', '', line[3:])
            result.append(Paragraph(inline(label), styles['heading']))
        elif not line.strip():
            flush()
        else:
            paragraph.append(line.strip())
    flush()
    return result


def render(source, target, expected_pages, reflection=False):
    styles = getSampleStyleSheet()
    custom = {
        'title': ParagraphStyle('DocTitle', fontName='Helvetica-Bold', fontSize=20,
                                leading=25, spaceAfter=17, textColor=colors.HexColor('#153b58')),
        'heading': ParagraphStyle('DocHeading', fontName='Helvetica-Bold', fontSize=14,
                                  leading=19, spaceBefore=10, spaceAfter=13,
                                  textColor=colors.HexColor('#153b58')),
        'body': ParagraphStyle('DocBody', parent=styles['BodyText'], fontName='Helvetica',
                              fontSize=11 if reflection else 10, leading=16 if reflection else 14.5,
                              spaceAfter=10, alignment=TA_LEFT),
        'code': ParagraphStyle('DocCode', fontName='Courier', fontSize=8.1, leading=12,
                              leftIndent=8, spaceBefore=6, spaceAfter=12),
    }
    text = source.read_text(encoding='utf-8')
    sections = text.split('<div style="page-break-after: always;"></div>')
    story = []
    for index, section in enumerate(sections):
        if index:
            story.append(PageBreak())
        story.extend(flow(section, custom))
    doc = SimpleDocTemplate(str(target), pagesize=A4, rightMargin=49, leftMargin=49,
                            topMargin=48, bottomMargin=48, title=source.stem,
                            author='Northwind take-home candidate', pageCompression=1)

    def footer(sheet, document):
        sheet.saveState()
        sheet.setStrokeColor(colors.HexColor('#d7e0e6'))
        sheet.line(49, 36, A4[0] - 49, 36)
        sheet.setFont('Helvetica', 8)
        sheet.setFillColor(colors.HexColor('#536878'))
        sheet.drawString(49, 23, 'NWG-D0BC | Northwind Group | FY2024')
        sheet.drawRightString(A4[0] - 49, 23, f'{document.page} / {expected_pages}')
        sheet.restoreState()

    def stable_canvas(*args, **kwargs):
        kwargs['invariant'] = 1
        return canvas.Canvas(*args, **kwargs)

    doc.build(story, onFirstPage=footer, onLaterPages=footer, canvasmaker=stable_canvas)
    count = len(PdfReader(target).pages)
    if count != expected_pages:
        raise ValueError(f'{target.name}: {count} pages, expected {expected_pages}; revise layout')
    return {'source': source.name, 'file': target.name, 'pages': count,
            'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
            'sha256': hashlib.sha256(target.read_bytes()).hexdigest()}


def main():
    out = ROOT / 'output/pdf'
    out.mkdir(parents=True, exist_ok=True)
    manifest = {'renderer': f'reportlab {Version}', 'documents': [
        render(ROOT / 'ARCHITECTURE.md', out / 'ARCHITECTURE.pdf', 6),
        render(ROOT / 'REFLECTION.md', out / 'REFLECTION.pdf', 1, reflection=True),
    ]}
    (out / 'pdf_manifest.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    print('Rendered architecture: 6 pages; reflection: 1 page.')


if __name__ == '__main__':
    main()
