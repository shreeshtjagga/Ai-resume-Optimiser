import io
import re
import logging

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import HRFlowable, Paragraph, SimpleDocTemplate, Spacer

logger = logging.getLogger(__name__)

DARK    = colors.HexColor("#0d1b2a")
ACCENT  = colors.HexColor("#1f4e79")
MID     = colors.HexColor("#4a4a4a")
BODY    = colors.HexColor("#1a1a1a")
RULE_LT = colors.HexColor("#b0b8c1")

def _build_styles() -> dict:
    return {
        "name": ParagraphStyle(
            "Name",
            fontSize=20, fontName="Helvetica-Bold",
            alignment=TA_CENTER,
            spaceBefore=0, spaceAfter=3, leading=24,
            textColor=DARK,
        ),
        "contact_field": ParagraphStyle(
            "ContactField",
            fontSize=9, fontName="Helvetica",
            alignment=TA_CENTER,
            spaceBefore=0, spaceAfter=1, leading=13,
            textColor=MID,
        ),
        "contact_line": ParagraphStyle(
            "ContactLine",
            fontSize=9, fontName="Helvetica",
            alignment=TA_CENTER,
            spaceBefore=0, spaceAfter=6, leading=13,
            textColor=MID,
        ),
        "section": ParagraphStyle(
            "Section",
            fontSize=10.5, fontName="Helvetica-Bold",
            spaceBefore=12, spaceAfter=2, leading=14,
            textColor=ACCENT,
        ),
        "normal": ParagraphStyle(
            "Normal",
            fontSize=9.5, fontName="Helvetica",
            leading=14, spaceAfter=2,
            textColor=BODY,
        ),
        "bullet": ParagraphStyle(
            "Bullet",
            fontSize=9.5, fontName="Helvetica",
            leading=14, spaceAfter=2,
            leftIndent=12, textColor=BODY,
        ),
        "role": ParagraphStyle(
            "Role",
            fontSize=10, fontName="Helvetica-Bold",
            leading=14, spaceAfter=0, spaceBefore=6,
            textColor=DARK,
        ),
        "meta": ParagraphStyle(
            "Meta",
            fontSize=9, fontName="Helvetica-Oblique",
            leading=13, spaceAfter=3,
            textColor=MID,
        ),
        "degree": ParagraphStyle(
            "Degree",
            fontSize=10, fontName="Helvetica-Bold",
            leading=14, spaceAfter=0, spaceBefore=4,
            textColor=DARK,
        ),
        "institution": ParagraphStyle(
            "Institution",
            fontSize=9.5, fontName="Helvetica",
            leading=13, spaceAfter=1,
            textColor=BODY,
        ),
    }

_SECTION_HEADINGS = {
    "SUMMARY", "EDUCATION", "TECHNICAL SKILLS",
    "INTERNSHIP & EXPERIENCE", "PROJECTS",
    "CERTIFICATIONS", "RELEVANT COURSEWORK",
}

_EMPTY_PHRASES = {
    "no experience listed", "no internship listed", "no certifications listed",
    "no relevant coursework listed", "no data available", "not provided",
    "n/a", "none", "no information provided", "no experience provided",
    "no internship experience listed", "no certifications provided",
    "no internship & experience listed",
}

# Regex patterns to catch filler sentences the AI invents despite instructions.
# Any line fully matching one of these is silently dropped from the PDF.
_FILLER_PATTERNS = [
    re.compile(r"^no\s+\w[\w\s&]*listed[\.,]?", re.I),
    re.compile(r"^no\s+\w[\w\s&]*provided[\.,]?", re.I),
    re.compile(r"^no\s+\w[\w\s&]*available[\.,]?", re.I),
    re.compile(r"projects?\s+demonstrate\s+relevant", re.I),
    re.compile(r"however[,\s]+projects?\s+", re.I),
    re.compile(r"view\s+certificate", re.I),
    re.compile(r"^-\s*view\s+certificate", re.I),
    re.compile(r"certification.*view\s+cert", re.I),
    re.compile(r"^not\s+applicable[\.,]?$", re.I),
    re.compile(r"^n/?a[\.,]?$", re.I),
    re.compile(r"no\s+data\s+(found|available|provided)", re.I),
]

_CONTACT_LABELS = {
    "email":    re.compile(r"email[:\s]*", re.I),
    "phone":    re.compile(r"phone[:\s]*", re.I),
    "linkedin": re.compile(r"linkedin[:\s]*", re.I),
    "github":   re.compile(r"github[:\s]*", re.I),
}

def _safe(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _is_section_heading(line: str) -> bool:
    return line.strip().upper() in _SECTION_HEADINGS


def _is_empty_placeholder(line: str) -> bool:
    stripped = line.strip()
    if stripped.lower() in _EMPTY_PHRASES:
        return True
    return any(pat.search(stripped) for pat in _FILLER_PATTERNS)


def _is_bullet(line: str) -> bool:
    return line.startswith(("-", "•", "*"))


def _is_meta_line(line: str) -> bool:
    return ("|" in line or "–" in line) and "@" not in line and len(line) < 120


def _looks_like_contact(line: str) -> bool:
    low = line.lower()
    return any(kw in low for kw in ("@", "phone", "linkedin", "github", "email", "+91", "+1"))


def _split_contact_into_fields(line: str) -> list[str]:
    parts = [p.strip() for p in line.split("|")]
    return [p for p in parts if p]


def _render_contact_block(story: list, line: str, styles: dict) -> None:
    fields = _split_contact_into_fields(line)

    location_fields = []
    email_phone     = []
    social_fields   = []

    for f in fields:
        fl = f.lower()
        if "linkedin" in fl or "github" in fl:
            social_fields.append(f)
        elif "@" in f or "email" in fl or "phone" in fl or re.search(r"\+?\d[\d\s\-]{6,}", f):
            email_phone.append(f)
        else:
            location_fields.append(f)

    rows = []
    if location_fields:
        rows.append(" | ".join(location_fields))
    if email_phone:
        rows.append("   •   ".join(email_phone))
    if social_fields:
        rows.append("   •   ".join(social_fields))
    if not rows:
        rows = fields

    for row in rows:
        story.append(Paragraph(_safe(row), styles["contact_field"]))

    story.append(Spacer(1, 4))
    story.append(HRFlowable(width="100%", thickness=1.2, color=DARK, spaceAfter=8, spaceBefore=2))


def _section_rule(story: list) -> None:
    story.append(
        HRFlowable(width="100%", thickness=0.6, color=ACCENT, spaceAfter=4, spaceBefore=1)
    )


def generate_pdf(text: str) -> bytes:
    if not text.strip():
        raise ValueError("Cannot generate PDF from empty text.")

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        leftMargin=20 * mm, rightMargin=20 * mm,
        topMargin=16 * mm, bottomMargin=16 * mm,
    )

    styles = _build_styles()
    story: list = []
    lines = [ln.rstrip() for ln in text.split("\n")]
    n = len(lines)

    header_lines: list[str] = []
    body_start = 0
    blank_streak = 0

    for idx, raw in enumerate(lines):
        ln = raw.strip()

        if _is_section_heading(ln):
            body_start = idx
            break

        if not ln:
            blank_streak += 1
            if blank_streak >= 2 and header_lines:
                body_start = idx + 1
                break
            continue

        blank_streak = 0
        header_lines.append(ln)
    else:
        body_start = n

    # Render name — always the very first non-empty header line
    if header_lines:
        story.append(Paragraph(_safe(header_lines[0]), styles["name"]))

    for ln in header_lines[1:]:
        if _looks_like_contact(ln) or "|" in ln:
            _render_contact_block(story, ln, styles)
        else:
            story.append(Paragraph(_safe(ln), styles["contact_line"]))

    if header_lines and not any(
        isinstance(el, HRFlowable) for el in story
    ):
        story.append(HRFlowable(width="100%", thickness=1.2, color=DARK, spaceAfter=8))

    i = body_start
    current_section: str | None = None

    while i < n:
        raw = lines[i]
        line = raw.strip()

        if not line:
            story.append(Spacer(1, 3))
            i += 1
            continue

        if _is_empty_placeholder(line):
            i += 1
            continue

        if _is_section_heading(line):
            current_section = line.upper()
            story.append(Paragraph(line.upper(), styles["section"]))
            _section_rule(story)
            i += 1
            continue

        if _is_bullet(line):
            clean = line.lstrip("-•* ").strip()
            story.append(Paragraph(f"• {_safe(clean)}", styles["bullet"]))
            i += 1
            continue

        if current_section == "EDUCATION":
            if _is_meta_line(line):
                story.append(Paragraph(_safe(line), styles["institution"]))
            else:
                story.append(Paragraph(_safe(line), styles["degree"]))
            i += 1
            continue

        if current_section in ("INTERNSHIP & EXPERIENCE", "PROJECTS"):
            if _is_meta_line(line):
                story.append(Paragraph(_safe(line), styles["meta"]))
            else:
                story.append(Paragraph(_safe(line), styles["role"]))
            i += 1
            continue

        story.append(Paragraph(_safe(line), styles["normal"]))
        i += 1

    try:
        doc.build(story)
    except Exception as e:
        logger.error(f"ReportLab PDF build failed: {e}")
        raise RuntimeError(f"PDF generation failed: {e}") from e

    return buffer.getvalue()