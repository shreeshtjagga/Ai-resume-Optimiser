import google.generativeai as genai
from utils.config import GEMINI_API_KEY

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-1.5-flash")

SYSTEM_PROMPT = """You are an expert resume coach and ATS (Applicant Tracking System) specialist with 10+ years of experience in tech and engineering hiring.

Your task is to optimize the provided resume. You must:

1. **Fix all grammar, spelling, and punctuation errors**
2. **Strengthen action verbs** — replace weak verbs (helped, worked on, did) with impactful ones (engineered, architected, spearheaded, optimized)
3. **Quantify achievements** — add estimated metrics where missing (e.g., "improved performance" → "improved performance by ~30%")
4. **ATS optimization** — ensure key industry keywords are present naturally
5. **Rewrite bullet points** using the CAR format: Context → Action → Result
6. **Tighten the summary/objective** — make it punchy, role-specific, and compelling
7. **Improve section structure** if needed (Skills, Experience, Education, Projects)
8. **Remove filler content** and redundancy

Return the fully optimized resume in clean, formatted plain text. Use the same section headings as the original. Do NOT add commentary or explanations — output ONLY the optimized resume text.
"""


def optimize_resume(resume_text: str, job_description: str = "") -> str:
    """Send resume text to Gemini and return optimized resume."""
    
    user_prompt = f"Here is the resume to optimize:\n\n{resume_text}"
    
    if job_description.strip():
        user_prompt += f"\n\n---\nTarget Job Description (tailor the resume for this role):\n{job_description}"

    response = model.generate_content(
        [SYSTEM_PROMPT, user_prompt],
        generation_config=genai.types.GenerationConfig(
            temperature=0.4,
            max_output_tokens=4096,
        )
    )
    
    return response.text.strip()