# AI Recruiter System

An intelligent candidate ranking platform that matches job descriptions to candidates using LLM-powered skill extraction. Paste a job description, and the system parses real technical requirements, scores every candidate in the database against them, and returns a ranked shortlist with matched/missing skills.

🔗 **Live demo:** [(https://ai-recruiter-engine-void-main.vercel.app/)](https://ai-recruiter-engine-void-main.vercel.app/)
🔗 **API:** [test2-ox8y.onrender.com](https://test2-ox8y.onrender.com)

---

## How it works

1. The user pastes a job description into the frontend.
2. The backend sends it to an LLM (via [Groq](https://groq.com), running Llama 3.1) to extract real technical skills, role, and seniority — explicitly filtering out vague terms like "general."
3. Every candidate in the dataset is scored against the extracted requirements, combining:
   - **JD match score** (70%) — overlap between required skills and candidate skills
   - **Profile score** (30%) — the candidate's overall pre-computed profile strength
   - **Role-based boosts** — small bonuses for relevant titles (e.g. frontend/backend/ML signals)
4. Results are ranked, deduplicated, and the top K candidates are returned with their matched and missing skills.

### Built-in fallbacks

The system is designed to degrade gracefully rather than fail silently:

| Situation | Behavior |
|---|---|
| LLM extraction succeeds | Full skill/role/seniority extraction |
| LLM unavailable or returns nothing | Falls back to keyword matching against a known skills list |
| JD is too vague for keywords (e.g. "Frontend Developer") | Falls back to a role → baseline-skills mapping |
| Nothing can be extracted at all | Returns top candidates by general profile strength, flagged so the UI shows an informational note instead of a hard error |

---

## Tech stack

**Backend**
- FastAPI (Python)
- [Groq](https://groq.com) (Llama 3.1 8B Instant) for job description parsing — OpenAI-compatible API
- Deployed on [Render](https://render.com)

**Frontend**
- React + Vite
- Axios for API calls
- Deployed on [Vercel](https://vercel.com)

---

## Project structure

```
Backend/
├── main.py                 # FastAPI app, routes, request/response models
├── recruiter_engine.py     # Scoring engine, skill extraction fallback chain
├── llm_job_parser.py       # Groq API integration for JD parsing
├── scored_candidates.json  # Candidate dataset
└── requirements.txt

Frontend/
├── src/
│   ├── App.jsx              # Main UI: search form, results grid
│   └── App.css
└── package.json
```

---

## Running locally

### Backend

```bash
cd Backend
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements.txt
```

Create a `.env` file in `Backend/`:

```
GROQ_API_KEY=your-groq-key-here
```

Get a free key at [console.groq.com/keys](https://console.groq.com/keys) — no credit card required.

```bash
uvicorn main:app --reload --port 8080
```

Visit `http://127.0.0.1:8080/docs` for interactive API docs, or `http://127.0.0.1:8080/health` to confirm the LLM client is connected.

### Frontend

```bash
cd Frontend
npm install
```

Create a `.env` file in `Frontend/` to point at your local backend:

```
VITE_BACKEND_URL=http://127.0.0.1:8080
```

```bash
npm run dev
```

---

## API

### `POST /rank_candidates`

**Request body:**
```json
{
  "job_description": "Backend developer with Python, SQL, and API experience",
  "top_k": 5,
  "use_llm": true
}
```

**Response:**
```json
{
  "success": true,
  "count": 5,
  "used_llm": true,
  "generic_ranking": false,
  "top_candidates": [
    {
      "candidate_id": "CAND_0000001",
      "current_title": "backend engineer",
      "years_experience": 6.9,
      "location": "toronto",
      "skills": ["python", "sql", "..."],
      "jd_score": 66.67,
      "profile_score": 75,
      "final_score": 79.17,
      "matched_skills": ["python", "sql"],
      "missing_skills": ["api"]
    }
  ]
}
```

### `GET /health`

Returns whether the Groq client initialized successfully — useful for confirming the API key is configured correctly in production.

---

## Notes on the dataset

`scored_candidates.json` contains 66,000+ synthetic candidate profiles, each pre-scored on technical, behavioral, logistics, and role fit dimensions, used as the `profile_score` baseline that combines with live JD matching.

---

## License

MIT
