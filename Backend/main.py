from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware

from recruiter_engine import get_top_candidates

app = FastAPI(title="AI Recruiter API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def home():
    return {"message": "AI Recruiter API Running 🚀"}


# 🔥 ERROR-PROOF ENDPOINT (NO 422 ANYMORE)
@app.post("/rank_candidates")
async def rank_candidates(request: Request):

    try:
        body = await request.json()

        job_description = body.get("job_description", "")
        top_k = int(body.get("top_k", 5))

        if not job_description.strip():
            raise HTTPException(
                status_code=400,
                detail="job_description is required"
            )

        candidates = get_top_candidates(job_description, top_k)

        return {
            "success": True,
            "count": len(candidates),
            "top_candidates": candidates
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }