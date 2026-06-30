from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from recruiter_engine import get_top_candidates

try:
    from llm_job_parser import client as llm_client
except Exception:
    llm_client = None

app = FastAPI(title="AI Recruiter API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class RankRequest(BaseModel):
    job_description: str
    top_k: int = 5
    use_llm: bool = True  # default to True so the LLM path is used unless explicitly disabled


@app.get("/")
def root():
    return {"status": "running"}


@app.get("/health")
def health():
    """Quick check you can hit in the browser to confirm the Groq LLM client is live."""
    return {
        "status": "running",
        "llm_provider": "groq",
        "llm_available": llm_client is not None,
    }


@app.post("/rank_candidates")
def rank(request: RankRequest):

    if not request.job_description.strip():
        raise HTTPException(400, "Empty JD")

    try:
        candidates, generic_ranking = get_top_candidates(
            request.job_description,
            request.top_k,
            use_llm=request.use_llm,
        )
    except Exception as e:
        # surface real errors instead of letting them 500 silently
        raise HTTPException(500, f"Ranking failed: {e}")

    return {
        "success": True,
        "count": len(candidates),
        "used_llm": request.use_llm,
        "generic_ranking": generic_ranking,
        "top_candidates": candidates,
    }