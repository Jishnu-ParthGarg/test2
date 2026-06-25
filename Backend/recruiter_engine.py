from pathlib import Path
from functools import lru_cache
import json

from jd_parser import extract_jd_requirements
from jd_matcher import calculate_jd_score


# -------------------------
# CONFIG
# -------------------------

PROFILE_WEIGHT = 0.60
JD_WEIGHT = 0.40

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_FILE = BASE_DIR / "scored_candidates.json"


# -------------------------
# LOAD CANDIDATES
# -------------------------

@lru_cache(maxsize=1)
def load_candidates():

    if not DATA_FILE.exists():
        raise FileNotFoundError(f"{DATA_FILE} not found")

    with open(DATA_FILE, "r", encoding="utf-8") as f:
        candidates = json.load(f)

    if not isinstance(candidates, list):
        raise ValueError("scored_candidates.json must contain a list")

    return candidates


# -------------------------
# MAIN ENGINE
# -------------------------

def get_top_candidates(job_description: str, top_k: int = 10):

    candidates = load_candidates()

    requirements = extract_jd_requirements(job_description)

    ranked = []

    for candidate in candidates:

        profile_score = candidate.get("final_score", 0)

        jd_score = calculate_jd_score(
            candidate,
            requirements
        )

        final_score = (
            profile_score * PROFILE_WEIGHT
            + jd_score * JD_WEIGHT
        )

        candidate_copy = candidate.copy()

        candidate_copy["jd_score"] = round(jd_score, 2)
        candidate_copy["final_score"] = round(final_score, 2)

        ranked.append(candidate_copy)

    ranked.sort(
        key=lambda x: x["final_score"],
        reverse=True
    )

    return ranked[:top_k]