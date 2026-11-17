"""Render docs/executive_summary.md as a one-page A4 PDF.

Run from the repo root:
    python scripts/generate_executive_pdf.py
"""

import re
import sys
from pathlib import Path

from reportlab.lib.enums import TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "docs" / "executive_summary.md"
OUT = ROOT / "docs" / "executive_summary.pdf"

BOLD = re.compile(r"\*\*(.+?)\*\*")


def inline(text: str) -> str:
    return BOLD.sub(r"<b>\1</b>", text)


def build_styles():
    styles = getSampleStyleSheet()
    title = ParagraphStyle(
        "ExecTitle",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=16,
        leading=20,
        alignment=0,
        spaceAfter=6,
    )
    tagline = ParagraphStyle(
        "ExecTagline",
        parent=styles["Normal"],
        fontName="Helvetica-Oblique",
        fontSize=10,
        leading=13,
        alignment=0,
        spaceAfter=8,
    )
    body = ParagraphStyle(
        "ExecBody",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=9.5,
        leading=12.5,
        alignment=TA_JUSTIFY,
        spaceAfter=5,
    )
    small = ParagraphStyle("ExecSmall", parent=body, fontSize=7.5, leading=10)
    return title, tagline, body, small


def main():
    text = SRC.read_text(encoding="utf-8")
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]

    title, tagline, body, small = build_styles()
    story = []

    for line in lines:
        if line.startswith("# "):
            story.append(Paragraph(inline(line[2:]), title))
            continue
        if line.startswith("**"):
            story.append(Paragraph(inline(line), tagline))
            continue
        if line == "---":
            continue
        if line.startswith("## ") or line.startswith("- "):
            story.append(Paragraph(inline(re.sub(r"^[#-]+ ", "", line)), body))
            continue
        story.append(Paragraph(inline(line), body))

    story.append(Spacer(1, 6))
    story.append(Paragraph(
        "Demonstration uses simulated data; real-world validation is a stated future step. "
        "More detail: docs/sentinel_paper.md.",
        small,
    ))

    doc = SimpleDocTemplate(
        str(OUT),
        pagesize=A4,
        title="Sentinel — Executive Summary",
        author="Dhansika.R",
        subject="On-premises, clinician-in-the-loop psychophysiological triage",
        leftMargin=2.2 * cm,
        rightMargin=2.2 * cm,
        topMargin=2.0 * cm,
        bottomMargin=2.0 * cm,
    )

    def footer(canvas, docobj):
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.drawCentredString(A4[0] / 2, 1.1 * cm, "Sentinel — Executive Summary")
        canvas.drawRightString(A4[0] - 2.2 * cm, 1.1 * cm, str(docobj.page))
        canvas.restoreState()

    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    print(f"wrote {OUT} ({OUT.stat().st_size} bytes, {doc.page} page(s))")


if __name__ == "__main__":
    sys.exit(main())