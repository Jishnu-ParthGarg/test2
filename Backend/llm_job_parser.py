import os
import json
from typing import Dict

from dotenv import load_dotenv
load_dotenv()

from openai import OpenAI

# =====================================================
# GROQ CLIENT (OpenAI-compatible API, free tier)
# =====================================================
try:
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY not found in environment / .env file")

    client = OpenAI(
        api_key=api_key,
        base_url="https://api.groq.com/openai/v1",
    )
    print("✅ Groq client created successfully")
except Exception as e:
    print(f"❌ Groq client failed: {e}")
    client = None


# Fast + free Groq model. Other options: "llama-3.1-70b-versatile" (slower, smarter)
GROQ_MODEL = "llama-3.1-8b-instant"


def build_job_prompt(job_description: str) -> str:
    return f"""
Extract structured hiring intent.

Return ONLY valid JSON. No explanation, no markdown, no code fences.

RULES:
- skills MUST be real technical skills
- NEVER use "general"
- MUST NOT hallucinate vague terms

JOB:
{job_description}

FORMAT:
{{
  "role": "frontend|backend|ml|data|general",
  "skills": ["python", "react", "sql"],
  "seniority": "junior|mid|senior"
}}
"""


def call_llm(prompt: str) -> Dict:

    if client is None:
        return {}

    try:
        res = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": "Return ONLY strict JSON. No text, no markdown fences."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.0
        )
    except Exception as e:
        print(f"⚠️ Groq API call failed: {e}")
        return {}

    text = res.choices[0].message.content.strip()

    # strip markdown code fences if the model adds them anyway
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:].strip()

    # 🔥 HARD JSON FIX (THIS IS CRITICAL)
    try:
        return json.loads(text)
    except Exception:
        # fallback: extract JSON block
        try:
            start = text.find("{")
            end = text.rfind("}") + 1
            return json.loads(text[start:end])
        except Exception as e:
            print(f"⚠️ Could not parse LLM output as JSON: {e}\nRaw output: {text[:200]}")
            return {}


def parse_job(job_description: str) -> Dict:

    if not job_description:
        return {}

    result = call_llm(build_job_prompt(job_description))

    if not isinstance(result, dict):
        return {}

    skills = result.get("skills", [])

    cleaned = []
    for s in skills:
        if isinstance(s, str):
            s = s.strip().lower()
            if s and s != "general":
                cleaned.append(s)

    return {
        "role": (result.get("role") or "").lower(),
        "skills": cleaned,
        "seniority": result.get("seniority") or ""
    }