import streamlit as st
from pathlib import Path
from services.pdf_service import extract_text_from_pdf
from services.docx_service import extract_text_from_docx
from services.ai_service import optimize_resume
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from reportlab.lib import colors
import io

def generate_pdf(text: str) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4,
        leftMargin=18*mm, rightMargin=18*mm,
        topMargin=15*mm, bottomMargin=15*mm)

    styles = getSampleStyleSheet()

    name_style = ParagraphStyle("Name", fontSize=18, fontName="Helvetica-Bold",
        alignment=TA_CENTER, spaceAfter=2, textColor=colors.HexColor("#1a1a2e"))

    contact_style = ParagraphStyle("Contact", fontSize=9, fontName="Helvetica",
        alignment=TA_CENTER, spaceAfter=8, textColor=colors.HexColor("#444444"))

    section_style = ParagraphStyle("Section", fontSize=11, fontName="Helvetica-Bold",
        spaceBefore=10, spaceAfter=3, textColor=colors.HexColor("#1a1a2e"),
        borderPadding=(0, 0, 2, 0))

    normal_style = ParagraphStyle("Normal", fontSize=9.5, fontName="Helvetica",
        leading=14, spaceAfter=3, textColor=colors.HexColor("#222222"))

    bullet_style = ParagraphStyle("Bullet", fontSize=9.5, fontName="Helvetica",
        leading=14, spaceAfter=2, leftIndent=12, textColor=colors.HexColor("#222222"))

    job_style = ParagraphStyle("Job", fontSize=10, fontName="Helvetica-Bold",
        leading=14, spaceAfter=1, textColor=colors.HexColor("#1a1a2e"))

    story = []
    lines = text.split("\n")
    i = 0

    while i < len(lines):
        line = lines[i].strip()
        if not line:
            story.append(Spacer(1, 3))
            i += 1
            continue

        # First non-empty line = name
        if i == 0 or (i < 3 and story == []):
            story.append(Paragraph(line, name_style))
            i += 1
            continue

        # Contact line (has | or @ or phone-like)
        if ("|" in line or "@" in line) and len(line) < 120:
            line = line.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            story.append(Paragraph(line, contact_style))
            story.append(HRFlowable(width="100%", thickness=1,
                color=colors.HexColor("#1a1a2e"), spaceAfter=6))
            i += 1
            continue

        # Section headings (ALL CAPS)
        if line.isupper() and len(line) > 2:
            story.append(Spacer(1, 4))
            story.append(Paragraph(line, section_style))
            story.append(HRFlowable(width="100%", thickness=0.5,
                color=colors.HexColor("#cccccc"), spaceAfter=4))
            i += 1
            continue

        # Bullet points
        if line.startswith("-") or line.startswith("•"):
            line = line.lstrip("-•").strip()
            line = line.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            story.append(Paragraph(f"• {line}", bullet_style))
            i += 1
            continue

        # Job title lines (has | separator)
        if "|" in line and len(line) < 100:
            line = line.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            story.append(Paragraph(line, job_style))
            i += 1
            continue

        # Normal text
        line = line.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        story.append(Paragraph(line, normal_style))
        i += 1

    doc.build(story)
    return buffer.getvalue()


st.set_page_config(page_title="AI Resume Optimizer",)
st.title("AI Resume Optimizer")
st.caption("Upload your resume → get a professional ATS-optimized version instantly.")
st.divider()

uploaded_file = st.file_uploader("Upload Resume (PDF or DOCX)", type=["pdf", "docx", "doc"])
job_desc = st.text_area("Job Description (optional)", height=120,
    placeholder="Paste job description to tailor the resume to a specific role...")

if st.button("Optimize", type="primary", use_container_width=True):
    if not uploaded_file:
        st.warning("Please upload a resume.")
    else:
        ext = Path(uploaded_file.name).suffix.lower()
        file_bytes = uploaded_file.read()

        with st.spinner("Reading resume..."):
            try:
                resume_text = extract_text_from_pdf(file_bytes) if ext == ".pdf" else extract_text_from_docx(file_bytes)
            except Exception as e:
                st.error(f"Error reading file: {e}")
                st.stop()

        if not resume_text.strip():
            st.error("No text found. File might be scanned/image-based.")
            st.stop()

        with st.spinner("Optimizing your resume..."):
            try:
                st.session_state["optimized"] = optimize_resume(resume_text, job_desc)
            except Exception as e:
                st.error(f"Groq error: {e}")
                st.stop()

if "optimized" in st.session_state:
    st.divider()
    st.subheader("Optimized Resume")
    st.text_area("", value=st.session_state["optimized"], height=400, label_visibility="collapsed")
    st.download_button(
        label="Download as PDF",
        data=generate_pdf(st.session_state["optimized"]),
        file_name="optimized_resume.pdf",
        mime="application/pdf",
        use_container_width=True,
    )