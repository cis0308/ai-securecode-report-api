from pathlib import Path
from html import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont


# =========================
# Korean Font
# =========================

BASE_DIR = Path(__file__).resolve().parent.parent
FONT_PATH = BASE_DIR / "fonts" / "malgun.ttf"

FONT_NAME = "Malgun"

if FONT_PATH.exists():
    pdfmetrics.registerFont(TTFont(FONT_NAME, str(FONT_PATH)))
else:
    # 폰트 파일이 없으면 PDF 생성은 되지만 한글이 깨질 수 있음
    FONT_NAME = "Helvetica"


# =========================
# Styles
# =========================

TITLE_STYLE = ParagraphStyle(
    name="KoreanTitle",
    fontName=FONT_NAME,
    fontSize=18,
    leading=24,
    alignment=TA_CENTER,
    spaceAfter=18,
)

HEADING_STYLE = ParagraphStyle(
    name="KoreanHeading",
    fontName=FONT_NAME,
    fontSize=13,
    leading=18,
    spaceBefore=12,
    spaceAfter=8,
)

NORMAL_STYLE = ParagraphStyle(
    name="KoreanNormal",
    fontName=FONT_NAME,
    fontSize=10,
    leading=15,
    alignment=TA_LEFT,
    wordWrap="CJK",
)

CODE_STYLE = ParagraphStyle(
    name="KoreanCode",
    fontName=FONT_NAME,
    fontSize=8,
    leading=11,
    wordWrap="CJK",
    backColor=colors.HexColor("#f8fafc"),
    borderColor=colors.HexColor("#e2e8f0"),
    borderWidth=0.5,
    borderPadding=6,
)


def safe_text(value) -> str:
    if value is None:
        return "-"
    return escape(str(value)).replace("\n", "<br/>")


def add_paragraph(story, text, style=NORMAL_STYLE):
    story.append(Paragraph(safe_text(text), style))


def generate_report(filename: str, result: dict, output_path: str) -> str:
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        rightMargin=36,
        leftMargin=36,
        topMargin=42,
        bottomMargin=36,
    )

    story = []

    story.append(Paragraph("AI SecureCode 보안약점 분석 보고서", TITLE_STYLE))

    add_paragraph(story, f"분석 대상: {filename}")
    add_paragraph(story, f"보안 점수: {result.get('security', {}).get('score', '-')}")
    add_paragraph(story, f"등급: {result.get('security', {}).get('grade', '-')}")
    story.append(Spacer(1, 14))

    summary = result.get("summary", {})

    table_data = [
        ["구분", "건수"],
        ["HIGH", str(summary.get("HIGH", 0))],
        ["MEDIUM", str(summary.get("MEDIUM", 0))],
        ["LOW", str(summary.get("LOW", 0))],
        ["TOTAL", str(result.get("total", 0))],
    ]

    table = Table(table_data, colWidths=[180, 120])
    table.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, -1), FONT_NAME),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eef4ff")),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#dbe3ef")),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]
        )
    )

    story.append(table)
    story.append(Spacer(1, 18))

    story.append(Paragraph("정적 분석 상세 결과", HEADING_STYLE))

    issues = result.get("issues", [])

    if not issues:
        add_paragraph(story, "탐지된 보안약점이 없습니다.")
    else:
        for issue in issues:
            story.append(Paragraph(
                f"[{safe_text(issue.get('issue_severity'))}] {safe_text(issue.get('test_name'))}",
                HEADING_STYLE,
            ))

            add_paragraph(story, f"분석도구: {issue.get('tool', 'Bandit')}")
            add_paragraph(story, f"CWE: {issue.get('cwe', '-')}")
            add_paragraph(story, f"행안부 보안약점 유형: {issue.get('mois', '-')}")
            add_paragraph(
                story,
                f"파일/라인: {issue.get('filename', '-')}:{issue.get('line_number', '-')}",
            )
            add_paragraph(story, f"설명: {issue.get('issue_text', '-')}")
            story.append(Spacer(1, 8))

    story.append(Spacer(1, 16))
    story.append(Paragraph("LLM 기반 보안 분석 결과", HEADING_STYLE))

    llm_text = result.get("llm_result", "LLM 분석 결과 없음")

    # Markdown 기호가 깨져 보이지 않도록 일반 텍스트 처리
    llm_text = (
        llm_text.replace("**", "")
        .replace("###", "")
        .replace("##", "")
        .replace("#", "")
    )

    for block in llm_text.split("\n"):
        if block.strip():
            add_paragraph(story, block)
        else:
            story.append(Spacer(1, 6))

    doc.build(story)

    return output_path