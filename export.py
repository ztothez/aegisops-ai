from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Preformatted
from reportlab.lib.enums import TA_LEFT
import io
import html
import re

def generate_pdf(technique_id: str, red_output: str, blue_output: str) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4,
                           rightMargin=inch, leftMargin=inch,
                           topMargin=inch, bottomMargin=inch)
    
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='CustomTitle',
                              fontSize=20, spaceAfter=20,
                              textColor=colors.HexColor('#1a1a2e'),
                              fontName='Helvetica-Bold'))
    styles.add(ParagraphStyle(name='SectionTitle',
                              fontSize=14, spaceAfter=10, spaceBefore=20,
                              textColor=colors.HexColor('#c0392b'),
                              fontName='Helvetica-Bold'))
    styles.add(ParagraphStyle(name='BlueSectionTitle',
                              fontSize=14, spaceAfter=10, spaceBefore=20,
                              textColor=colors.HexColor('#2980b9'),
                              fontName='Helvetica-Bold'))
    styles.add(ParagraphStyle(name='CodeStyle',
                              fontSize=8, fontName='Courier',
                              backColor=colors.HexColor('#f4f4f4'),
                              leftIndent=10, rightIndent=10,
                              spaceAfter=10))

    story = []
    
    # Title
    story.append(Paragraph("AegisOps AI Purple Team Report", styles['CustomTitle']))
    story.append(Paragraph(f"Technique: {html.escape(str(technique_id))}", styles['Normal']))
    story.append(Spacer(1, 20))

    # Red Team section
    story.append(Paragraph("Red Team Attack Simulation", styles['SectionTitle']))
    _parse_markdown_to_pdf(red_output, story, styles)
    
    story.append(Spacer(1, 20))
    
    # Blue Team section
    story.append(Paragraph("Blue Team Defense Report", styles['BlueSectionTitle']))
    _parse_markdown_to_pdf(blue_output, story, styles)

    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()

def _parse_markdown_to_pdf(text: str, story: list, styles):
    # Split on code blocks
    parts = re.split(r'```(?:\w+)?\n?', text)
    in_code = False
    for part in parts:
        if in_code:
            story.append(Preformatted(part.strip(), styles['CodeStyle']))
        else:
            for line in part.split('\n'):
                line = line.strip()
                if not line:
                    story.append(Spacer(1, 6))
                elif line.startswith('### '):
                    story.append(Paragraph(html.escape(line[4:]), styles['Heading3']))
                elif line.startswith('## '):
                    story.append(Paragraph(html.escape(line[3:]), styles['Heading2']))
                elif line.startswith('# '):
                    story.append(Paragraph(html.escape(line[2:]), styles['Heading1']))
                elif line.startswith('- ') or line.startswith('* '):
                    story.append(Paragraph(f"• {html.escape(line[2:])}", styles['Normal']))
                else:
                    story.append(Paragraph(html.escape(line), styles['Normal']))
        in_code = not in_code