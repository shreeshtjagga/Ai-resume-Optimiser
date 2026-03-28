import os
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
client = Groq(api_key=GROQ_API_KEY)

SYSTEM_PROMPT = """You are an expert resume coach and ATS (Applicant Tracking System) specialist with 10+ years of experience in tech and engineering hiring.

Your task is to optimize the provided resume. You must:

1. Fix all grammar, spelling, and punctuation errors
2. Strengthen action verbs — replace weak verbs (helped, worked on, did) with impactful ones (engineered, architected, spearheaded, optimized)
3. Quantify achievements — add estimated metrics where missing
4. ATS optimization — ensure key industry keywords are present naturally
5. Rewrite bullet points using the CAR format: Context → Action → Result
6. Tighten the summary/objective — make it punchy, role-specific, and compelling
7. Improve section structure if needed (Skills, Experience, Education, Projects)
8. Remove filler content and redundancy

Return the fully optimized resume in clean, formatted plain text. Use the same section headings as the original. Do NOT add commentary or explanations — output ONLY the optimized resume text.
"""


def optimize_resume(resume_text: str, job_description: str = "") -> str:
    user_prompt = f"Here is the resume to optimize:\n\n{resume_text}"

    if job_description.strip():
        user_prompt += f"\n\n---\nTarget Job Description (tailor the resume for this role):\n{job_description}"

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.4,
        max_tokens=4096,
    )

    return response.choices[0].message.content.strip()