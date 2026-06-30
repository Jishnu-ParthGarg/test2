from pathlib import Path
from functools import lru_cache
import json
import re
from typing import Dict, List, Set

# =====================================================
# OPTIONAL LLM JOB PARSER
# =====================================================
try:
    from llm_job_parser import parse_job
except:
    parse_job = None


# =====================================================
# CONFIG
# =====================================================

PROFILE_WEIGHT = 0.30
JD_WEIGHT = 0.70

BASE_DIR = Path(__file__).resolve().parent

DATA_PATHS = [
    BASE_DIR / "scored_candidates.json",
    BASE_DIR.parent / "scored_candidates.json",
]

# Used only when use_llm=False (no API call). Keep this list roughly in sync
# with the kinds of skill_names you expect in scored_candidates.json.
KNOWN_SKILLS = [
    "python", "java", "javascript", "typescript", "react", "node", "node.js",
    "sql", "nosql", "mongodb", "postgresql", "mysql", "aws", "azure", "gcp",
    "docker", "kubernetes", "django", "flask", "fastapi", "spring",
    "machine learning", "deep learning", "nlp", "computer vision",
    "tensorflow", "pytorch", "pandas", "numpy", "scikit-learn",
    "html", "css", "vue", "angular", "next.js", "graphql", "rest", "api",
    "git", "ci/cd", "linux", "c++", "c#", "go", "rust", "ruby", "php",
]


# =====================================================
# LOAD CANDIDATES
# =====================================================

@lru_cache(maxsize=1)
def load_candidates():
    for path in DATA_PATHS:
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)

            if isinstance(data, dict):
                data = data.get("data", [])

            return data

    raise RuntimeError("scored_candidates.json not found")


# =====================================================
# NON-LLM FALLBACK: simple keyword matching
# =====================================================

def extract_skills_keyword(jd: str) -> Set[str]:
    jd_lower = jd.lower()
    reqs: Set[str] = set()

    for skill in KNOWN_SKILLS:
        # word-boundary-ish match so "go" doesn't match inside "going"
        pattern = r"(?<![a-zA-Z0-9])" + re.escape(skill) + r"(?![a-zA-Z0-9])"
        if re.search(pattern, jd_lower):
            reqs.add(skill)

    return reqs


# =====================================================
# LLM-BASED EXTRACTION (NO "GENERAL" LEAKS)
# =====================================================

def extract_skills_llm(jd: str) -> Set[str]:

    job_data = {}

    if parse_job:
        try:
            job_data = parse_job(jd) or {}
        except Exception as e:
            print(f"⚠️ parse_job failed: {e}")
            job_data = {}
    else:
        print("⚠️ parse_job not available (llm_job_parser failed to import)")

    skills = job_data.get("skills", []) or []
    role = job_data.get("role", "") or ""

    reqs: Set[str] = set()

    for s in skills:
        if isinstance(s, str):
            s = s.strip().lower()
            if s and s != "general":
                reqs.add(s)

    role = role.strip().lower()
    if role and role != "general":
        reqs.add(role)

    return reqs


def extract_skills(jd: str, use_llm: bool = True) -> Set[str]:
    if use_llm:
        reqs = extract_skills_llm(jd)
        # graceful degrade: if the LLM path returned nothing (e.g. API
        # hiccup, vague JD), still try keyword matching rather than
        # returning a hard empty result.
        if not reqs:
            reqs = extract_skills_keyword(jd)
        return reqs

    return extract_skills_keyword(jd)


# =====================================================
# SCORING
# =====================================================

def calculate_score(candidate: Dict, reqs: Set[str]):

    skills = set(map(str.lower, candidate.get("skills", [])))

    matched = skills & reqs
    missing = reqs - skills

    jd_score = (len(matched) / max(len(reqs), 1)) * 100

    return jd_score, list(matched), list(missing)


# =====================================================
# MAIN ENGINE
# =====================================================

def get_top_candidates(job_description: str, top_k: int = 10, use_llm: bool = True):

    candidates = load_candidates()
    reqs = extract_skills(job_description, use_llm=use_llm)

    if not reqs:
        # genuinely nothing usable extracted (even keyword fallback found nothing)
        return []

    ranked = []

    for c in candidates:

        profile = float(c.get("final_score", 0) or 0)

        jd_score, matched, missing = calculate_score(c, reqs)

        # optional boost logic
        role_boost = 0
        skills = set(map(str.lower, c.get("skills", [])))
        jd_text = job_description.lower()

        if any(k in jd_text for k in ["frontend", "ui", "react"]) and "react" in skills:
            role_boost += 10

        if any(k in jd_text for k in ["backend", "api", "server"]) and ("python" in skills or "node" in skills):
            role_boost += 10

        if any(k in jd_text for k in ["ai", "ml", "machine"]) and c.get("has_ml"):
            role_boost += 10

        final_score = (
            jd_score * JD_WEIGHT +
            profile * PROFILE_WEIGHT +
            role_boost
        )

        ranked.append({
            "candidate_id": c.get("candidate_id", ""),
            "current_title": c.get("current_title", "Unknown Title"),
            "years_experience": c.get("years_experience", 0),
            "location": c.get("location", "N/A"),

            "skill_names": c.get("skills", []),
            "skills": c.get("skills", []),

            "jd_score": round(jd_score, 2),
            "profile_score": round(profile, 2),
            "final_score": round(final_score, 2),

            "matched_skills": matched,
            "missing_skills": missing,
        })

    ranked.sort(key=lambda x: x["final_score"], reverse=True)

    # diversity filter
    seen = set()
    output = []

    for r in ranked:
        if r["candidate_id"] not in seen:
            output.append(r)
            seen.add(r["candidate_id"])

        if len(output) == top_k:
            break

    return output