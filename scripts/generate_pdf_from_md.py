#!/usr/bin/env python3
"""Simple Markdown -> PDF generator using ReportLab.

This script performs a lightweight conversion: it parses headings and paragraphs
and writes a readable PDF. It avoids heavy markdown features and focuses on
producing a clean PDF of the report in `diagrams/design_patterns_report.md`.
"""
import os
import sys
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, ListFlowable, ListItem
from reportlab.lib.units import mm
from reportlab.lib import colors


def parse_markdown_lines(lines):
    """Very small markdown parser: headings (#, ##), bullet lists (-) and paragraphs."""
    elements = []
    i = 0
    while i < len(lines):
        line = lines[i].rstrip('\n')
        if not line.strip():
            i += 1
            continue
        if line.startswith('# '):
            elements.append(('h1', line[2:].strip()))
            i += 1
            continue
        if line.startswith('## '):
            elements.append(('h2', line[3:].strip()))
            i += 1
            continue
        # bullet list
        if line.lstrip().startswith('- '):
            items = []
            while i < len(lines) and lines[i].lstrip().startswith('- '):
                items.append(lines[i].lstrip()[2:].strip())
                i += 1
            elements.append(('ul', items))
            continue
        # code fence: include as preformatted block
        if line.startswith('```'):
            i += 1
            code_lines = []
            while i < len(lines) and not lines[i].startswith('```'):
                code_lines.append(lines[i].rstrip('\n'))
                i += 1
            i += 1
            elements.append(('code', '\n'.join(code_lines)))
            continue
        # paragraph (collect contiguous lines)
        para_lines = [line]
        i += 1
        while i < len(lines) and lines[i].strip() and not lines[i].startswith('#') and not lines[i].lstrip().startswith('- '):
            para_lines.append(lines[i].rstrip('\n'))
            i += 1
        elements.append(('p', ' '.join([l.strip() for l in para_lines])))
    return elements


def build_pdf(md_path, pdf_path):
    with open(md_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    elems = parse_markdown_lines(lines)

    doc = SimpleDocTemplate(pdf_path, pagesize=A4,
                            rightMargin=20*mm, leftMargin=20*mm,
                            topMargin=20*mm, bottomMargin=20*mm)
    styles = getSampleStyleSheet()
    # custom styles (이미 존재하면 건너뜀)
    try:
        styles.add(ParagraphStyle(name='Heading1', parent=styles['Heading1'], fontSize=16, leading=20, spaceAfter=8))
    except KeyError:
        pass
    try:
        styles.add(ParagraphStyle(name='Heading2', parent=styles['Heading2'], fontSize=13, leading=16, spaceAfter=6))
    except KeyError:
        pass
    try:
        styles.add(ParagraphStyle(name='Code', fontName='Courier', fontSize=8, leading=10, backColor=colors.whitesmoke))
    except KeyError:
        pass

    story = []
    story.append(Paragraph('Design Patterns Report', styles['Heading1']))
    story.append(Spacer(1, 6))

    for kind, content in elems:
        if kind == 'h1':
            story.append(Paragraph(content, styles['Heading1']))
        elif kind == 'h2':
            story.append(Paragraph(content, styles['Heading2']))
        elif kind == 'p':
            story.append(Paragraph(content, styles['Normal']))
            story.append(Spacer(1, 4))
        elif kind == 'ul':
            lf = ListFlowable([ListItem(Paragraph(it, styles['Normal']), leftIndent=10) for it in content], bulletType='bullet')
            story.append(lf)
            story.append(Spacer(1, 6))
        elif kind == 'code':
            # render as paragraph with monospace
            for line in content.split('\n'):
                story.append(Paragraph(line.replace(' ', '&nbsp;'), styles['Code']))
            story.append(Spacer(1, 6))

    doc.build(story)


def main():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    md = os.path.join(root, 'diagrams', 'design_patterns_report.md')
    pdf = os.path.join(root, 'diagrams', 'design_patterns_report.pdf')
    if not os.path.exists(md):
        print('Markdown file not found:', md)
        return 2
    build_pdf(md, pdf)
    print('Wrote PDF:', pdf)
    return 0


if __name__ == '__main__':
    sys.exit(main())
