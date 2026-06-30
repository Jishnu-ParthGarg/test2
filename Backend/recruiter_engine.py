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

# Last-resort fallback when a JD is too short/vague for the LLM or keyword
# matcher to extract anything (e.g. just "Frontend Developer"). Maps a role
# hint found anywhere in the JD text to a baseline real skill set, so a bare
# title still produces a sensible ranking instead of an empty result.
ROLE_SKILL_FALLBACK = {
    "frontend": {"html", "css", "javascript", "react"},
    "front-end": {"html", "css", "javascript", "react"},
    "front end": {"html", "css", "javascript", "react"},
    "backend": {"python", "sql", "api", "node"},
    "back-end": {"python", "sql", "api", "node"},
    "back end": {"python", "sql", "api", "node"},
    "full stack": {"javascript", "react", "node", "sql", "api"},
    "fullstack": {"javascript", "react", "node", "sql", "api"},
    "ml": {"python", "machine learning", "sql"},
    "machine learning": {"python", "machine learning", "sql"},
    "ai": {"python", "machine learning", "sql"},
    "data scien": {"python", "sql", "machine learning"},
    "data engineer": {"python", "sql", "aws"},
    "devops": {"docker", "kubernetes", "ci/cd", "aws"},
    "mobile": {"react", "javascript"},
}


def extract_skills_role_fallback(jd: str) -> Set[str]:
    jd_lower = jd.lower()
    reqs: Set[str] = set()

    for keyword, skillset in ROLE_SKILL_FALLBACK.items():
        if keyword in jd_lower:
            reqs |= skillset

    return reqs


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
    else:
        reqs = extract_skills_keyword(jd)

    # last resort: bare role titles like "Frontend Developer" with no other
    # detail. Map known role keywords to a baseline real skill set.
    if not reqs:
        reqs = extract_skills_role_fallback(jd)

    return reqs


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
        # Absolute last resort: nothing could be extracted at all (no LLM
        # skills, no keyword matches, no role match). Rather than return an
        # empty result, show the strongest general candidates by profile
        # score so the user/judge still sees something useful. The caller
        # (main.py) is responsible for surfacing `generic_ranking=True`.
        fallback = sorted(
            candidates,
            key=lambda c: float(c.get("final_score", 0) or 0),
            reverse=True,
        )[:top_k]

        return [
            {
                "candidate_id": c.get("candidate_id", ""),
                "current_title": c.get("current_title", "Unknown Title"),
                "years_experience": c.get("years_experience", 0),
                "location": c.get("location", "N/A"),
                "skill_names": c.get("skills", []),
                "skills": c.get("skills", []),
                "jd_score": 0,
                "profile_score": round(float(c.get("final_score", 0) or 0), 2),
                "final_score": round(float(c.get("final_score", 0) or 0), 2),
                "matched_skills": [],
                "missing_skills": [],
            }
            for c in fallback
        ], True  # generic_ranking flag

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

    return output, False  # generic_ranking flag