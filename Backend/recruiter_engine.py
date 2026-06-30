from pathlib import Path
from functools import lru_cache
import json
import re
from typing import Dict, Set


# =====================================================
# CONFIG
# =====================================================

PROFILE_WEIGHT = 0.20
JD_WEIGHT = 0.80

BASE_DIR = Path(__file__).resolve().parent

POSSIBLE_DATA_FILES = [
    BASE_DIR / "scored_candidates.json",
    BASE_DIR.parent / "scored_candidates.json",
]


# =====================================================
# SKILL TAXONOMY
# =====================================================

MASTER_SKILLS = {
    "python", "java", "javascript", "react", "html", "css",
    "machine learning", "deep learning", "statistics",
    "rag", "llm", "langchain", "faiss", "pinecone",
    "tensorflow", "pytorch", "scikit-learn",
    "nlp", "opencv", "yolo"
}

ALIASES = {
    "reactjs": "react",
    "react.js": "react",
    "nodejs": "node.js",
    "llms": "llm",
    "vector db": "vector database",
}


SEMANTIC_MAP = {
    "machine learning": {"tensorflow", "pytorch", "scikit-learn", "deep learning"},
    "statistics": {"pandas", "numpy", "data science"},
    "rag": {"langchain", "faiss", "pinecone"},
    "frontend": {"react", "javascript", "html", "css"},
}


# =====================================================
# LOAD DATA (SAFE)
# =====================================================

@lru_cache(maxsize=1)
def load_candidates():

    data_file = None

    for path in POSSIBLE_DATA_FILES:
        if path.exists():
            data_file = path
            break

    if data_file is None:
        raise FileNotFoundError("scored_candidates.json not found in any known path")

    with open(data_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list):
        raise ValueError("scored_candidates.json must be a LIST of candidates")

    return data


# =====================================================
# JD PARSER
# =====================================================

def extract_jd_requirements(job_description: str) -> Set[str]:

    jd = (job_description or "").lower()
    jd = re.sub(r"[^a-z0-9+#.\s]", " ", jd)

    tokens = set(jd.split())

    detected = set()

    for skill in MASTER_SKILLS:

        normalized = ALIASES.get(skill, skill)

        if " " in skill:
            if skill in jd:
                detected.add(normalized)
        else:
            if skill in tokens:
                detected.add(normalized)

    return detected


# =====================================================
# SCORING ENGINE
# =====================================================

def calculate_jd_score(candidate: Dict, requirements: Set[str]):

    if not requirements:
        return 5.0, [], list(requirements)

    skills = set(map(str.lower, candidate.get("skill_names", [])))

    matched = set()

    # direct match
    matched |= skills & requirements

    # semantic match
    for req in requirements:
        if req in SEMANTIC_MAP and skills & SEMANTIC_MAP[req]:
            matched.add(req)

    # feature boosts
    if candidate.get("has_python") and "python" in requirements:
        matched.add("python")

    if candidate.get("has_ml") and any(x in requirements for x in ["machine learning", "deep learning"]):
        matched.add("machine learning")

    if candidate.get("has_retrieval_experience") and "rag" in requirements:
        matched.add("rag")

    missing = requirements - matched

    score = (len(matched) / max(len(requirements), 1)) * 100

    return round(score, 2), list(matched), list(missing)


# =====================================================
# MAIN ENGINE (LINKEDIN STYLE FIXED)
# =====================================================

def get_top_candidates(job_description: str, top_k: int = 10):

    try:
        candidates = load_candidates()
    except Exception as e:
        raise RuntimeError(f"Candidate load failed: {str(e)}")

    requirements = extract_jd_requirements(job_description)
    jd_text = (job_description or "").lower()

    # 🔥 IMPORTANT FIX: fallback prevents identical outputs
    if not requirements:
        requirements = {"python", "javascript"}

    ranked = []

    for c in candidates:

        profile = c.get("final_score", 0)

        try:
            profile = float(profile)
        except:
            profile = 0.0

        profile = min(profile, 100)

        jd_score, matched, missing = calculate_jd_score(c, requirements)

        # -----------------------------
        # ROLE BIAS (CRITICAL FIX)
        # -----------------------------
        role_boost = 0

        skills = set(map(str.lower, c.get("skill_names", [])))

        if ("frontend" in jd_text or "react" in jd_text):
            if "react" in skills:
                role_boost += 10

        if ("machine learning" in jd_text or "data science" in jd_text):
            if c.get("has_ml"):
                role_boost += 10

        if ("rag" in jd_text or "llm" in jd_text):
            if c.get("has_retrieval_experience"):
                role_boost += 10

        # -----------------------------
        # FINAL SCORE (STABLE + JD DRIVEN)
        # -----------------------------
        final_score = (
            (jd_score ** 1.1) * JD_WEIGHT +
            profile * PROFILE_WEIGHT +
            role_boost
        )

        ranked.append({
            "candidate_id": c.get("candidate_id", "UNKNOWN"),
            "title": c.get("current_title", ""),

            # frontend compatibility
            "skills": c.get("skill_names", []),
            "skill_names": c.get("skill_names", []),

            "jd_score": jd_score,
            "profile_score": profile,
            "final_score": round(final_score, 2),

            "matched_skills": matched,
            "missing_skills": missing,

            "explanation": f"Matched {len(matched)}/{len(requirements)} skills"
        })

    ranked.sort(key=lambda x: x["final_score"], reverse=True)

    # -----------------------------
    # DIVERSITY FILTER (LinkedIn-style)
    # -----------------------------
    final = []
    seen = set()

    for r in ranked:

        key = tuple(sorted(r["matched_skills"][:2]))

        if key not in seen:
            final.append(r)
            seen.add(key)

        if len(final) == top_k:
            break

    return final


# =====================================================
# TEST
# =====================================================

if __name__ == "__main__":

    jd = """
    AI Engineer
    Python Machine Learning RAG LangChain
    """

    results = get_top_candidates(jd, 5)

    for r in results:
        print(r["candidate_id"], r["final_score"], r["skills"])