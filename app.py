import streamlit as st
import os
from pathlib import Path
from services.pdf_service import extract_text_from_pdf
from services.docx_service import extract_text_from_docx
from services.ai_service import optimize_resume
from utils.config import ALLOWED_EXTENSIONS, MAX_FILE_SIZE_MB

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="AI Resume Optimizer",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=DM+Mono:wght@300;400;500&display=swap');

:root {
    --bg: #0a0a0f;
    --surface: #111118;
    --border: #1e1e2e;
    --accent: #7c6af7;
    --accent2: #f7c26a;
    --text: #e8e8f0;
    --muted: #6b6b80;
    --success: #4ade80;
}

html, body, [data-testid="stAppViewContainer"] {
    background-color: var(--bg) !important;
    color: var(--text) !important;
    font-family: 'Syne', sans-serif !important;
}

[data-testid="stHeader"] { background: transparent !important; }
[data-testid="stSidebar"] { background: var(--surface) !important; }

/* Title */
.hero-title {
    font-family: 'Syne', sans-serif;
    font-size: 3.2rem;
    font-weight: 800;
    letter-spacing: -1px;
    background: linear-gradient(135deg, #7c6af7 0%, #f7c26a 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    margin: 0;
    line-height: 1.1;
}

.hero-sub {
    font-family: 'DM Mono', monospace;
    font-size: 0.85rem;
    color: var(--muted);
    letter-spacing: 2px;
    text-transform: uppercase;
    margin-top: 0.5rem;
}

/* Upload box */
[data-testid="stFileUploader"] {
    background: var(--surface) !important;
    border: 1px dashed var(--border) !important;
    border-radius: 12px !important;
    padding: 1rem !important;
}

[data-testid="stFileUploader"]:hover {
    border-color: var(--accent) !important;
}

/* Text areas */
.stTextArea textarea {
    background: var(--surface) !important;
    border: 1px solid var(--border) !important;
    border-radius: 10px !important;
    color: var(--text) !important;
    font-family: 'DM Mono', monospace !important;
    font-size: 0.82rem !important;
}

.stTextArea textarea:focus {
    border-color: var(--accent) !important;
    box-shadow: 0 0 0 2px rgba(124,106,247,0.2) !important;
}

/* Button */
.stButton > button {
    background: linear-gradient(135deg, var(--accent), #9d8df5) !important;
    color: white !important;
    border: none !important;
    border-radius: 10px !important;
    font-family: 'Syne', sans-serif !important;
    font-weight: 700 !important;
    font-size: 1rem !important;
    padding: 0.75rem 2.5rem !important;
    letter-spacing: 0.5px !important;
    transition: all 0.2s ease !important;
    width: 100%;
}

.stButton > button:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 8px 24px rgba(124,106,247,0.35) !important;
}

/* Result box */
.result-box {
    background: var(--surface);
    border: 1px solid var(--border);
    border-left: 3px solid var(--accent);
    border-radius: 12px;
    padding: 1.5rem;
    font-family: 'DM Mono', monospace;
    font-size: 0.82rem;
    line-height: 1.8;
    color: var(--text);
    white-space: pre-wrap;
    max-height: 600px;
    overflow-y: auto;
}

/* Section labels */
.section-label {
    font-family: 'DM Mono', monospace;
    font-size: 0.72rem;
    color: var(--muted);
    text-transform: uppercase;
    letter-spacing: 2px;
    margin-bottom: 0.5rem;
}

/* Tag chips */
.chip {
    display: inline-block;
    background: rgba(124,106,247,0.12);
    color: var(--accent);
    border: 1px solid rgba(124,106,247,0.25);
    border-radius: 20px;
    padding: 2px 12px;
    font-family: 'DM Mono', monospace;
    font-size: 0.72rem;
    margin: 2px;
}

/* Divider */
.divider {
    border: none;
    border-top: 1px solid var(--border);
    margin: 2rem 0;
}

/* Success message */
.success-msg {
    background: rgba(74,222,128,0.08);
    border: 1px solid rgba(74,222,128,0.2);
    border-radius: 8px;
    padding: 0.75rem 1rem;
    color: var(--success);
    font-family: 'DM Mono', monospace;
    font-size: 0.82rem;
}

/* Hide streamlit branding */
#MainMenu, footer, [data-testid="stToolbar"] { visibility: hidden; }

/* Scrollbar */
::-webkit-scrollbar { width: 4px; }
::-webkit-scrollbar-track { background: var(--bg); }
::-webkit-scrollbar-thumb { background: var(--border); border-radius: 4px; }
</style>
""", unsafe_allow_html=True)


# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("""
<div style="padding: 2rem 0 1rem 0;">
    <p class="hero-sub">⚡ Powered by Google Gemini</p>
    <h1 class="hero-title">AI Resume<br>Optimizer</h1>
    <p style="color: #6b6b80; font-family: 'DM Mono', monospace; font-size: 0.82rem; margin-top: 1rem;">
        Upload your resume → Get ATS-optimized, impact-driven content in seconds.
    </p>
    <div style="margin-top: 0.75rem;">
        <span class="chip">PDF</span>
        <span class="chip">DOCX</span>
        <span class="chip">ATS Optimized</span>
        <span class="chip">Gemini 1.5 Flash</span>
    </div>
</div>
<hr class="divider">
""", unsafe_allow_html=True)


# ── Layout: two columns ───────────────────────────────────────────────────────
col1, col2 = st.columns([1, 1], gap="large")

with col1:
    st.markdown('<p class="section-label">01 — Upload Resume</p>', unsafe_allow_html=True)
    
    uploaded_file = st.file_uploader(
        label="Drop your resume here",
        type=["pdf", "docx", "doc"],
        help="Supports PDF and Word documents up to 10MB",
        label_visibility="collapsed"
    )

    if uploaded_file:
        file_size_mb = uploaded_file.size / (1024 * 1024)
        ext = Path(uploaded_file.name).suffix.lower()

        if file_size_mb > MAX_FILE_SIZE_MB:
            st.error(f"File too large ({file_size_mb:.1f}MB). Max allowed: {MAX_FILE_SIZE_MB}MB.")
        elif ext not in ALLOWED_EXTENSIONS:
            st.error("Unsupported file type. Please upload PDF or DOCX.")
        else:
            st.markdown(f'<div class="success-msg">✓ Loaded: <strong>{uploaded_file.name}</strong> ({file_size_mb:.2f} MB)</div>', unsafe_allow_html=True)
            st.session_state["file_ok"] = True
            st.session_state["uploaded_file"] = uploaded_file
            st.session_state["ext"] = ext
    else:
        st.session_state["file_ok"] = False

    st.markdown('<br><p class="section-label">02 — Job Description (Optional)</p>', unsafe_allow_html=True)
    job_desc = st.text_area(
        label="Paste the job description to tailor the resume",
        height=180,
        placeholder="Paste the job description here to get a role-specific optimized resume...",
        label_visibility="collapsed"
    )

    st.markdown("<br>", unsafe_allow_html=True)
    optimize_btn = st.button("⚡ Optimize My Resume", use_container_width=True)


# ── Processing ────────────────────────────────────────────────────────────────
with col2:
    st.markdown('<p class="section-label">03 — Optimized Resume</p>', unsafe_allow_html=True)

    if optimize_btn:
        if not st.session_state.get("file_ok"):
            st.warning("Please upload a resume file first.")
        else:
            uploaded = st.session_state["uploaded_file"]
            ext = st.session_state["ext"]
            file_bytes = uploaded.read()

            with st.spinner("Extracting text from your resume..."):
                try:
                    if ext == ".pdf":
                        resume_text = extract_text_from_pdf(file_bytes)
                    else:
                        resume_text = extract_text_from_docx(file_bytes)
                except Exception as e:
                    st.error(f"Failed to extract text: {e}")
                    st.stop()

            if not resume_text.strip():
                st.error("Could not extract text. The file might be scanned or image-based.")
                st.stop()

            with st.spinner("Gemini is optimizing your resume..."):
                try:
                    optimized = optimize_resume(resume_text, job_desc)
                    st.session_state["optimized"] = optimized
                except Exception as e:
                    st.error(f"Gemini API error: {e}")
                    st.stop()

    if "optimized" in st.session_state:
        optimized_text = st.session_state["optimized"]
        
        st.markdown(f'<div class="result-box">{optimized_text}</div>', unsafe_allow_html=True)
        
        st.markdown("<br>", unsafe_allow_html=True)
        st.download_button(
            label="⬇ Download Optimized Resume (.txt)",
            data=optimized_text,
            file_name="optimized_resume.txt",
            mime="text/plain",
            use_container_width=True,
        )
    else:
        st.markdown("""
        <div style="
            background: #111118;
            border: 1px dashed #1e1e2e;
            border-radius: 12px;
            padding: 3rem 2rem;
            text-align: center;
            color: #3a3a50;
            font-family: 'DM Mono', monospace;
            font-size: 0.82rem;
        ">
            <div style="font-size: 2rem; margin-bottom: 1rem;">📄</div>
            Your optimized resume will appear here.<br>
            Upload a file and hit <span style="color: #7c6af7;">Optimize</span>.
        </div>
        """, unsafe_allow_html=True)

# ── Footer ────────────────────────────────────────────────────────────────────
st.markdown("""
<hr class="divider">
<p style="text-align:center; font-family:'DM Mono',monospace; font-size:0.72rem; color:#3a3a50;">
    Built with Streamlit · Google Gemini 1.5 Flash · Python
</p>
""", unsafe_allow_html=True)