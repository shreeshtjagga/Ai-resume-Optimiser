from pathlib import Path
import streamlit as st
from services.ai_service import optimize_resume
from services.docx_service import extract_text_from_docx
from services.pdf_service import extract_text_from_pdf
from utils.pdf_generator import generate_pdf
from utils.ats_scorer import score_resume, ATSResult

st.set_page_config(
    page_title="AI Resume Optimizer",
    layout="centered",
)

SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".doc"}
MAX_FILE_SIZE_MB = 10


def _read_resume(file_bytes: bytes, extension: str) -> str:
    if extension == ".pdf":
        return extract_text_from_pdf(file_bytes)
    return extract_text_from_docx(file_bytes)


def _file_too_large(file_bytes: bytes) -> bool:
    return len(file_bytes) > MAX_FILE_SIZE_MB * 1024 * 1024


def _render_ats_score(result: ATSResult, label: str) -> None:
    color = result.grade_color
    score = result.total
    grade = result.grade

    st.markdown(
        f"""
        <div style="text-align:center; padding: 12px 0 4px 0;">
            <span style="font-size:48px; font-weight:700; color:{color};">{score}</span>
            <span style="font-size:20px; color:{color};">/100</span><br>
            <span style="font-size:15px; font-weight:600; color:{color};">{grade}</span><br>
            <span style="font-size:12px; color:#888;">{label}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.progress(score / 100)
    with st.expander("Score breakdown"):
        breakdown = {
            " Sections":      (result.section_score,      25),
            " Action Verbs":  (result.action_verb_score,  20),
            " Metrics":       (result.metrics_score,      20),
            " Keywords":      (result.keyword_score,      15),
            " Formatting":    (result.formatting_score,   10),
            " Contact Info":  (result.contact_score,      10),
        }
        for label_b, (got, out_of) in breakdown.items():
            pct = got / out_of
            bar_color = "#22c55e" if pct >= 0.75 else "#f59e0b" if pct >= 0.5 else "#ef4444"
            st.markdown(
                f"<div style='display:flex; justify-content:space-between; font-size:13px;'>"
                f"<span>{label_b}</span>"
                f"<span style='color:{bar_color}; font-weight:600;'>{got}/{out_of}</span>"
                f"</div>",
                unsafe_allow_html=True,
            )
            st.progress(pct)

    if result.feedback:
        with st.expander(" Tips to improve"):
            for tip in result.feedback:
                st.markdown(f"- {tip}")


st.markdown("h1  style='text-align:center;'> AI Resume Optimizer</h1>",unsafe_allow_html=True)
st.markdown('<p style="text-align:center; color:gray;">Upload your resume to get an ATS-optimized version instantly.</p>', unsafe_allow_html=True)
st.divider()

uploaded_file = st.file_uploader(
    "Upload Resume (PDF or DOCX)",
    type=["pdf", "docx", "doc"],
    help="Text-selectable PDFs and DOCX files are supported. Scanned/image PDFs are not.",
)

job_desc = st.text_area(
    "Job Description (optional)",
    height=120,
    placeholder="Paste a job description to tailor the resume and improve keyword matching…",
)

optimize_clicked = st.button("Optimize Resume", type="primary", use_container_width=True)


if optimize_clicked:
    if not uploaded_file:
        st.warning(" Please upload a resume before clicking Optimize.")
        st.stop()

    ext = Path(uploaded_file.name).suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        st.error(f"Unsupported file type: `{ext}`. Please upload a PDF or DOCX.")
        st.stop()

    file_bytes = uploaded_file.read()

    if _file_too_large(file_bytes):
        st.error(f"File exceeds the {MAX_FILE_SIZE_MB} MB limit. Please upload a smaller file.")
        st.stop()

    with st.spinner("Reading your resume…"):
        try:
            resume_text = _read_resume(file_bytes, ext)
        except (ValueError, RuntimeError) as e:
            st.error(f"Could not read the file: {e}")
            st.stop()
        except Exception as e:
            st.error(f"Unexpected error while reading file: {e}")
            st.stop()

    before_score = score_resume(resume_text, job_desc)
    st.session_state["before_score"] = before_score
    st.session_state["original_filename"] = Path(uploaded_file.name).stem

    with st.spinner("Optimizing your Resume"):
        try:
            optimized_text, was_compacted = optimize_resume(resume_text, job_desc)
            st.session_state["optimized"] = optimized_text
            st.session_state["was_compacted"] = was_compacted
        except (ValueError, RuntimeError) as e:
            st.error(f"Optimization failed: {e}")
            st.stop()
        except Exception as e:
            st.error(f"Unexpected error during optimization: {e}")
            st.stop()

    after_score = score_resume(optimized_text, job_desc)
    st.session_state["after_score"] = after_score



if "optimized" in st.session_state:
    optimized_text: str = st.session_state["optimized"]
    original_name: str = st.session_state.get("original_filename", "resume")
    before: ATSResult = st.session_state["before_score"]
    after: ATSResult  = st.session_state["after_score"]

    st.divider()

    if st.session_state.get("was_compacted"):
        st.info(
            "**Your resume was long** — only the most essential content was kept "
            "to ensure it fits on a single page. The top 2 projects, top 2 bullets "
            "per role, and most relevant skills were selected.",
        )

    st.subheader("ATS Analysis Score")
    st.caption("The ATS score evaluates how well your resume is optimized for Applicant Tracking Systems, which many employers use to screen candidates. A higher score means better formatting, keyword matching, and overall structure for ATS parsing.")


    col_b, col_a = st.columns(2)
    with col_b:
        _render_ats_score(before, "Before Optimization")
    with col_a:
        _render_ats_score(after, "After Optimization")

    # Improvement banner
    delta = after.total - before.total
    if delta > 0:
        st.success(f"ATS score improved by **+{delta} points** after optimization!")
    elif delta == 0:
        st.info("ATS score unchanged — the resume was already well-structured.")
    else:
        st.warning(f" ATS score changed by {delta} points. Review the tips above.")

    st.divider()

    st.subheader("Optimized Resume")
    st.text_area(
        "Optimized resume text",
        value=optimized_text,
        height=420,
        label_visibility="collapsed",
    )

    col1, col2 = st.columns(2)

    with col1:
        try:
            pdf_bytes = generate_pdf(optimized_text)
            st.download_button(
                label="Download as PDF",
                data=pdf_bytes,
                file_name=f"{original_name}_optimized.pdf",
                mime="application/pdf",
                use_container_width=True,
            )
        except Exception as e:
            st.error(f"PDF generation failed: {e}")

    with col2:
        st.download_button(
            label=" Download as TXT",
            data=optimized_text.encode("utf-8"),
            file_name=f"{original_name}_optimized.txt",
            mime="text/plain",
            use_container_width=True,
        )

    st.button(
        " Optimize another resume",
        on_click=lambda: [st.session_state.pop(k, None)
                          for k in ("optimized", "before_score", "after_score")],
        use_container_width=True,
    )