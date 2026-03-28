import streamlit as st
from pathlib import Path
from services.pdf_service import extract_text_from_pdf
from services.docx_service import extract_text_from_docx
from services.ai_service import optimize_resume
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.enums import TA_LEFT
import io

def generate_pdf(text: str) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4,
        leftMargin=20*mm, rightMargin=20*mm,
        topMargin=20*mm, bottomMargin=20*mm)
    styles = getSampleStyleSheet()
    normal = ParagraphStyle("N", parent=styles["Normal"], fontSize=10, leading=15, spaceAfter=4)
    heading = ParagraphStyle("H", parent=styles["Normal"], fontSize=12, leading=16,
        fontName="Helvetica-Bold", spaceAfter=6, spaceBefore=10)
    story = []
    for line in text.split("\n"):
        line = line.strip()
        if not line:
            story.append(Spacer(1, 4))
        elif line.isupper() or (line.endswith(":") and len(line) < 40):
            story.append(Paragraph(line, heading))
        else:
            line = line.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            story.append(Paragraph(line, normal))
    doc.build(story)
    return buffer.getvalue()

st.set_page_config(page_title="AI Resume Optimizer", page_icon="⚡")
st.title("⚡ AI Resume Optimizer")
st.divider()

uploaded_file = st.file_uploader("Upload Resume (PDF or DOCX)", type=["pdf", "docx", "doc"])
job_desc = st.text_area("Job Description (optional)", height=120)

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

        with st.spinner("Optimizing..."):
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
        label="⬇ Download PDF",
        data=generate_pdf(st.session_state["optimized"]),
        file_name="optimized_resume.pdf",
        mime="application/pdf",
        use_container_width=True,
    )