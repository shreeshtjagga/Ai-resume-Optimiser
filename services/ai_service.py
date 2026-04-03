import logging
import time
import re as _re

logger = logging.getLogger(__name__)


LONG_RESUME_WORD_THRESHOLD = 400



_BASE_RULES = """
RULES_SECTION =
1. PRESERVE the candidate's exact name, email, phone, LinkedIn, and GitHub — never alter these. Do NOT include city, state, or any physical address in the output.
2. PRESERVE all real companies, institutions, degrees, dates, and project names — never invent or hallucinate facts.
3. Strengthen all bullet points using CAR format: Action Verb + Context + Result.
4. Use strong action verbs: engineered, developed, architected, optimised, deployed, built, designed, implemented, spearheaded.
5. Add quantitative metrics wherever plausible (accuracy %, speed improvement, user count, etc.).
6. SUMMARY: 2-3 lines — punchy, role-specific, mentions top skills and goal.
7. Remove filler words, passive voice, and weak verbs (helped, worked on, was responsible for).
8. Keep section headings EXACTLY as: SUMMARY, EDUCATION, TECHNICAL SKILLS, INTERNSHIP & EXPERIENCE, PROJECTS, CERTIFICATIONS. Do NOT add any new sections or headings.
9. CRITICAL — EMPTY SECTIONS: If a section has NO real data in the original resume, DO NOT include that section heading at all. Do NOT write any explanation or filler. Simply omit the entire section silently.
10. CRITICAL — CERTIFICATIONS: Only include a certification if it has a real name AND a real issuer. If the entry is vague (e.g. "View Certificate") OMIT it entirely.
11. Do NOT add commentary, notes, disclaimers, or any text outside the resume content.
12. Output ONLY the formatted resume — nothing else, no markdown code fences, no extra lines.
"""

_OUTPUT_FORMAT = """
OUTPUT FORMAT (include only sections that have data):

FULL NAME
Email: email@example.com | Phone: +91 XXXXXXXXXX | LinkedIn: linkedin.com/in/username | GitHub: github.com/username

SUMMARY
2-3 line punchy summary here.

EDUCATION
Degree Name
Institution Name
Year – Year | CGPA: X.X / 10

TECHNICAL SKILLS
Category: skill1, skill2, skill3

INTERNSHIP & EXPERIENCE
Role Title
Company Name | Month Year – Month Year
- Strong bullet with metric

PROJECTS
Project Name
- Strong bullet with metric

CERTIFICATIONS
Certification Name – Issuer (Year)

RELEVANT COURSEWORK
Course1, Course2, Course3
"""

SYSTEM_PROMPT = (
    "You are a professional resume writer with 15+ years of experience helping "
    "candidates land jobs at top tech companies.\n\n"
    "Rewrite the given resume to be polished, ATS-friendly, and impactful. "
    "Follow ALL rules below strictly:\n"
    + _BASE_RULES
    + _OUTPUT_FORMAT
)

COMPACT_SYSTEM_PROMPT = (
    "You are a professional resume writer with 15+ years of experience helping "
    "candidates land jobs at top tech companies.\n\n"
    "The candidate's resume is TOO LONG for a single page. Your job is to rewrite "
    "it into a STRICT SINGLE-PAGE format by keeping only the most essential content. "
    "Follow ALL rules below:\n"
    + _BASE_RULES
    + """
ADDITIONAL SINGLE-PAGE RULES (apply these on top of the base rules):
S1. PROJECTS: Keep at most 2 projects — choose the most impressive/relevant ones. Drop the rest entirely.
S2. BULLETS PER ROLE/PROJECT: Maximum 2 bullet points per role or project. Keep the strongest two, drop the rest.
S3. TECHNICAL SKILLS: Merge and deduplicate. Keep only the most relevant skills — maximum 4 categories, maximum 5 skills per category.
S4. RELEVANT COURSEWORK: OMIT this section entirely — it takes space without adding value for experienced candidates.
S5. SUMMARY: Keep to 2 lines maximum.
S6. EDUCATION: One entry only. No extra lines beyond degree, institution, year, CGPA.
S7. CERTIFICATIONS: Keep at most 2. Drop any that are not well-known or relevant.
S8. Every bullet point must be ONE line only — no wrapping. Be concise.
S9. The final output MUST fit on a single A4 page. When in doubt, cut content rather than keep it.
"""
    + _OUTPUT_FORMAT
)



_client = None

def _get_client():
    global _client
    if _client is None:
        import streamlit as st
        from groq import Groq
        api_key = st.secrets.get("GROQ_API_KEY")
        if not api_key:
            raise RuntimeError(
                "GROQ_API_KEY is missing from Streamlit secrets. "
                "Add it to .streamlit/secrets.toml."
            )
        _client = Groq(api_key=api_key)
    return _client



_SECTION_HEADINGS = {
    "SUMMARY", "EDUCATION", "TECHNICAL SKILLS",
    "INTERNSHIP & EXPERIENCE", "PROJECTS",
    "CERTIFICATIONS", "RELEVANT COURSEWORK",
}

_FILLER_LINE_PATTERNS = [
    _re.compile(r"^no\s+\w[\w\s&]*listed[\.\,]?", _re.I),
    _re.compile(r"^no\s+\w[\w\s&]*provided[\.\,]?", _re.I),
    _re.compile(r"^no\s+\w[\w\s&]*available[\.\,]?", _re.I),
    _re.compile(r"projects?\s+demonstrate\s+relevant", _re.I),
    _re.compile(r"however[,\s]+projects?\s+", _re.I),
    _re.compile(r"view\s+certificate", _re.I),
    _re.compile(r"certification.*view\s+cert", _re.I),
    _re.compile(r"^not\s+applicable[\.\,]?$", _re.I),
    _re.compile(r"^n/?a[\.\,]?$", _re.I),
    _re.compile(r"no\s+data\s+(found|available|provided)", _re.I),
]


def _is_filler(line: str) -> bool:
    s = line.strip()
    return bool(s) and any(p.search(s) for p in _FILLER_LINE_PATTERNS)


def _remove_empty_sections(text: str) -> str:
    lines = text.splitlines()
    result: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip().upper()
        if stripped in _SECTION_HEADINGS:
            section_heading = line
            body: list[str] = []
            j = i + 1
            while j < len(lines):
                if lines[j].strip().upper() in _SECTION_HEADINGS:
                    break
                body.append(lines[j])
                j += 1
            clean_body = [ln for ln in body if not _is_filler(ln)]
            if any(ln.strip() for ln in clean_body):
                result.append(section_heading)
                result.extend(clean_body)
            i = j
        else:
            result.append(line)
            i += 1
    return "\n".join(result)


def _is_long_resume(text: str) -> bool:
    word_count = len(text.split())
    line_count = len([l for l in text.splitlines() if l.strip()])
    return word_count > LONG_RESUME_WORD_THRESHOLD or line_count > 60



def optimize_resume(
    resume_text: str,
    job_description: str = "",
    *,
    retries: int = 2,
    retry_delay: float = 2.0,
) -> tuple[str, bool]:
    if not resume_text.strip():
        raise ValueError("Resume text is empty — nothing to optimise.")

    long = _is_long_resume(resume_text)
    prompt = COMPACT_SYSTEM_PROMPT if long else SYSTEM_PROMPT

    if long:
        logger.info(
            f"Long resume detected ({len(resume_text.split())} words). "
            "Using compact prompt to fit single page."
        )

    user_prompt = f"Here is the resume to optimise:\n\n{resume_text.strip()}"
    if job_description.strip():
        user_prompt += (
            f"\n\n---\n"
            f"Target Job Description (tailor the resume to highlight relevant skills for this role):\n"
            f"{job_description.strip()}"
        )

    last_error: Exception | None = None
    for attempt in range(retries + 1):
        try:
            response = _get_client().chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user",   "content": user_prompt},
                ],
                temperature=0.3,
                max_tokens=4096,
            )
            result = response.choices[0].message.content.strip()
            if not result:
                raise ValueError("Model returned an empty response.")
            return _remove_empty_sections(result), long

        except Exception as e:
            last_error = e
            if attempt < retries:
                logger.warning(
                    f"Groq API attempt {attempt + 1} failed: {e}. "
                    f"Retrying in {retry_delay}s…"
                )
                time.sleep(retry_delay)
            else:
                logger.error(f"All {retries + 1} Groq API attempts failed.")

    raise RuntimeError(
        f"Resume optimisation failed after {retries + 1} attempts: {last_error}"
    ) from last_error