import traceback

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from models import (
    CandidateRequest,
    RankingResponse,
)
from recruiter_engine import get_top_candidates


app = FastAPI(
    title="AI Recruiter API"
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Change after deployment
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def home():
    return {
        "message": "AI Recruiter Backend Running 🚀"
    }


@app.post(
    "/rank_candidates",
    response_model=RankingResponse
)
def rank_candidates(
    request: CandidateRequest
):

    # Extra safety check
    if not request.job_description.strip():
        raise HTTPException(
            status_code=400,
            detail="Job description cannot be empty"
        )

    top_k = max(
        1,
        min(request.top_k, 100)
    )

    try:

        candidates = get_top_candidates(
            request.job_description,
            top_k
        )

        return {
            "success": True,
            "count": len(candidates),
            "top_candidates": candidates
        }

   
    except Exception as e:
        print(traceback.format_exc())  # 🔥 THIS is critical
        raise HTTPException(status_code=500, detail=str(e))