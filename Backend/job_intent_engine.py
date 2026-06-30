from typing import Dict
import json

try:
    from openai import OpenAI
    client = OpenAI()
except:
    client = None


def build_prompt(jd: str) -> str:
    return f"""
Extract structured hiring intent from job description.

Return ONLY JSON.

JOB:
{jd}

FORMAT:
{{
  "role": "frontend|backend|ml|data|general",
  "skills": ["python", "react", "sql", "pytorch"],
  "seniority": "junior|mid|senior"
}}
"""


def parse_job(jd: str) -> Dict:

    if not jd:
        return {}

    if not client:
        return {}

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "Return only valid JSON."},
            {"role": "user", "content": build_prompt(jd)}
        ],
        temperature=0.1
    )

    try:
        data = json.loads(response.choices[0].message.content)

        return {
            "role": data.get("role", "general").lower(),
            "skills": [s.lower() for s in data.get("skills", [])],
            "seniority": data.get("seniority", "mid")
        }

    except:
        return {}