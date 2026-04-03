import re
from dataclasses import dataclass, field


_EXPECTED_SECTIONS = [
    "SUMMARY",
    "EDUCATION",
    "TECHNICAL SKILLS",
    "INTERNSHIP & EXPERIENCE",
    "PROJECTS",
    "CERTIFICATIONS",
    "RELEVANT COURSEWORK",
]

_ACTION_VERBS = {
    "engineered", "developed", "architected", "optimised", "optimized",
    "deployed", "built", "designed", "implemented", "spearheaded",
    "created", "launched", "led", "managed", "delivered", "automated",
    "reduced", "increased", "improved", "integrated", "migrated",
    "refactored", "streamlined", "collaborated", "analyzed", "analysed",
    "established", "maintained", "resolved", "mentored", "trained",
    "coordinated", "executed", "generated", "produced", "enhanced",
    "accelerated", "transformed", "scaled", "modelled", "modeled",
    "researched", "published", "presented", "supervised", "negotiated",
}

_METRIC_PATTERNS = [
    r"\d+\s*%",                      # 95%
    r"\d+\s*x\b",                    # 3x
    r"\d[\d,]*\s*\+?\s*users?",      # 10,000+ users
    r"\d[\d,]*\s*ms\b",              # 120ms
    r"\d[\d,]*\s*(?:seconds?|mins?|hours?)",
    r"(?:increased|reduced|improved|decreased|boosted)\D{0,20}\d",
    r"\$\s*\d",                      # $500
    r"\d+\s*(?:projects?|teams?|members?|clients?|systems?)",
]

_CONTACT_PATTERNS = {
    "email":    r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}",
    "phone":    r"[\+\d][\d\s\-\(\)]{7,}",
    "linkedin": r"linkedin\.com",
    "github":   r"github\.com",
}

_FILLER_WORDS = [
    r"\bresponsible for\b", r"\bworked on\b", r"\bhelped\b",
    r"\bassisted\b", r"\bwas involved\b", r"\bparticipated in\b",
]


@dataclass
class ATSResult:
    total: int                          # 0–100
    section_score: int                  # 0–25
    action_verb_score: int              # 0–20
    metrics_score: int                  # 0–20
    keyword_score: int                  # 0–15
    formatting_score: int               # 0–10
    contact_score: int                  # 0–10
    found_sections: list[str] = field(default_factory=list)
    missing_sections: list[str] = field(default_factory=list)
    feedback: list[str] = field(default_factory=list)

    @property
    def grade(self) -> str:
        if self.total >= 85:
            return "Excellent"
        if self.total >= 70:
            return "Good"
        if self.total >= 55:
            return "Fair"
        return "Needs Work"

    @property
    def grade_color(self) -> str:
        """Returns a CSS hex colour suitable for the score display."""
        if self.total >= 85:
            return "#22c55e"   # green
        if self.total >= 70:
            return "#f59e0b"   # amber
        if self.total >= 55:
            return "#f97316"   # orange
        return "#ef4444"       # red


def score_resume(text: str, job_description: str = "") -> ATSResult:
    """
    Score a resume string and return an ATSResult.
    Optionally pass a job description to factor in keyword matching.
    """
    if not text.strip():
        return ATSResult(
            total=0, section_score=0, action_verb_score=0,
            metrics_score=0, keyword_score=0,
            formatting_score=0, contact_score=0,
            feedback=["Resume is empty."],
        )

    lines = [ln.strip() for ln in text.splitlines()]
    text_lower = text.lower()
    feedback: list[str] = []
    found_sections = [s for s in _EXPECTED_SECTIONS if s in text.upper()]
    missing_sections = [s for s in _EXPECTED_SECTIONS if s not in text.upper()]
    core = {"SUMMARY", "EDUCATION", "TECHNICAL SKILLS", "PROJECTS"}
    core_found = len([s for s in found_sections if s in core])
    bonus_found = len([s for s in found_sections if s not in core])

    section_score = min(25, (core_found / len(core)) * 20 + bonus_found * 2)
    section_score = int(section_score)

    if missing_sections:
        feedback.append(f"Missing sections: {', '.join(missing_sections)}.")
    words = set(re.findall(r"\b[a-z]+\b", text_lower))
    verbs_used = words & _ACTION_VERBS
    verb_ratio = min(len(verbs_used) / 8, 1.0)   # 8 unique verbs = full marks
    action_verb_score = int(verb_ratio * 20)

    if action_verb_score < 10:
        feedback.append("Use more strong action verbs (engineered, deployed, optimized…).")
    metric_hits = sum(
        1 for pat in _METRIC_PATTERNS if re.search(pat, text, re.IGNORECASE)
    )
    metric_ratio = min(metric_hits / 5, 1.0)      # 5 metric patterns = full marks
    metrics_score = int(metric_ratio * 20)

    if metrics_score < 10:
        feedback.append("Add more quantified achievements (%, speed gains, user counts…).")
    if job_description.strip():
        jd_words = set(re.findall(r"\b[a-z]{4,}\b", job_description.lower()))
        resume_words = set(re.findall(r"\b[a-z]{4,}\b", text_lower))
        common = jd_words & resume_words
        match_ratio = min(len(common) / max(len(jd_words) * 0.3, 1), 1.0)
        keyword_score = int(match_ratio * 15)
        if keyword_score < 8:
            feedback.append("Resume keywords don't closely match the job description.")
    else:
        generic_kw = {
            "python", "java", "sql", "data", "analysis", "machine", "learning",
            "cloud", "api", "agile", "react", "node", "docker", "kubernetes",
            "communication", "leadership", "management", "research",
        }
        hits = len(words & generic_kw)
        keyword_score = min(int((hits / 6) * 15), 15)
    formatting_score = 0
    bullet_lines = [ln for ln in lines if ln.startswith(("•", "-", "*"))]
    if len(bullet_lines) >= 3:
        formatting_score += 4
    else:
        feedback.append("Add more bullet points to describe your experience and projects.")

    filler_found = any(re.search(p, text_lower) for p in _FILLER_WORDS)
    if not filler_found:
        formatting_score += 3
    else:
        feedback.append("Remove filler phrases like 'responsible for', 'worked on', 'helped'.")

    # Check that lines aren't excessively long (ATS parsers struggle > 120 chars)
    long_lines = [ln for ln in lines if len(ln) > 120]
    if not long_lines:
        formatting_score += 3
    else:
        feedback.append(f"{len(long_lines)} line(s) exceed 120 characters — shorten them.")
    contact_score = 0
    for field_name, pattern in _CONTACT_PATTERNS.items():
        if re.search(pattern, text, re.IGNORECASE):
            contact_score += 2   # 2 pts each × 4 fields = 8, +2 bonus below
    # small bonus if all 4 are present
    if contact_score >= 8:
        contact_score = 10
    elif contact_score == 0:
        feedback.append("No contact information found (email, phone, LinkedIn, GitHub).")

    total = min(
        100,
        section_score + action_verb_score + metrics_score +
        keyword_score + formatting_score + contact_score,
    )

    return ATSResult(
        total=total,
        section_score=section_score,
        action_verb_score=action_verb_score,
        metrics_score=metrics_score,
        keyword_score=keyword_score,
        formatting_score=formatting_score,
        contact_score=contact_score,
        found_sections=found_sections,
        missing_sections=missing_sections,
        feedback=feedback,
    )
