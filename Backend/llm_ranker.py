import os
from typing import List, Dict
import json
from dotenv import load_dotenv
load_dotenv()

from openai import OpenAI
try:
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY not found in environment / .env file")

    client = OpenAI(
        api_key=api_key,
        base_url="https://api.groq.com/openai/v1",
    )
except Exception as e:
    client = None


def llm_rerank_candidates(job_description: str, candidates: List[Dict], top_k: int = 10):

    if not client:
        return candidates[:top_k]

    candidates = candidates[:50]

    prompt = f"""
Rank candidates ONLY using provided data.

Return JSON:
{{
  "ranked": [
    {{"candidate_id": "...", "score": 0-100, "reason": "..."}}
  ]
}}

JOB:
{job_description}

CANDIDATES:
{json.dumps(candidates)}
"""

    try:
        res = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2
        )

        data = json.loads(res.choices[0].message.content)
        ranked = data.get("ranked", [])

        id_map = {c["candidate_id"]: c for c in candidates}

        output = []
        for r in ranked:
            cid = r.get("candidate_id")
            if cid in id_map:
                output.append({
                    **id_map[cid],
                    "llm_score": r.get("score", 0),
                    "llm_reason": r.get("reason", "")
                })

        return output[:top_k] if output else candidates[:top_k]

    except:
        return candidates[:top_k]