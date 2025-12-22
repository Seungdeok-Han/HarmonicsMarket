from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.units import mm
import io

md_path = 'reports/mc_dc_one_page_summary.md'
pdf_path = 'reports/mc_dc_one_page_summary.pdf'

# Read markdown source
with open(md_path, 'r', encoding='utf-8') as f:
    md = f.read()

# Convert simple markdown headings and paragraphs to paragraph objects
styles = getSampleStyleSheet()
normal = styles['Normal']
heading = styles['Heading1']
subheading = styles['Heading2']

story = []
for line in md.splitlines():
    line = line.strip()
    if not line:
        story.append(Spacer(1, 4 * mm))
        continue
    if line.startswith('# '):
        story.append(Paragraph(line[2:].strip(), heading))
    elif line.startswith('## '):
        story.append(Paragraph(line[3:].strip(), subheading))
    elif line.startswith('- '):
        story.append(Paragraph('• ' + line[2:].strip(), normal))
    elif line.startswith('  - '):
        story.append(Paragraph('&nbsp;&nbsp;&nbsp;• ' + line[4:].strip(), normal))
    else:
        story.append(Paragraph(line, normal))

    story.append(Spacer(1, 2 * mm))

# Build PDF
doc = SimpleDocTemplate(pdf_path, pagesize=A4, rightMargin=20*mm, leftMargin=20*mm, topMargin=20*mm, bottomMargin=20*mm)
doc.build(story)

print('PDF generated at:', pdf_path)
