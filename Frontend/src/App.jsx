import { useState } from "react";
import axios from "axios";
import "./App.css";

function App() {
  const [jobDescription, setJobDescription] = useState("");
  const [topK, setTopK] = useState(5);
  const [useLlm, setUseLlm] = useState(true);
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [darkMode, setDarkMode] = useState(false);

  const API_URL =
    import.meta.env.VITE_BACKEND_URL ||
    "https://test2-ox8y.onrender.com";

  const rankCandidates = async () => {
    if (!jobDescription.trim()) {
      setError("Please enter a job description.");
      return;
    }

    try {
      setLoading(true);
      setError("");
      setResults([]);

      const response = await axios.post(
        `${API_URL}/rank_candidates`,
        {
          job_description: jobDescription,
          top_k: Number(topK),
          use_llm: useLlm,
        },
        {
          timeout: 60000,
          headers: {
            "Content-Type": "application/json",
          },
        }
      );

      if (response.data.success) {
        setResults(response.data.top_candidates || []);
        if ((response.data.top_candidates || []).length === 0) {
          setError(
            "No matching candidates found. Try a more detailed job description, or check the use_llm toggle."
          );
        }
      } else {
        setError(response.data.detail || response.data.error || "Unknown backend error.");
      }
    } catch (err) {
      console.error(err);

      if (err.code === "ECONNABORTED") {
        setError(
          "The server is taking longer than expected. If the backend was asleep, please wait a few seconds and try again."
        );
      } else if (err.response) {
        // FastAPI's HTTPException returns errors under "detail", not "error".
        const backendMessage =
          err.response.data?.detail || err.response.data?.error || "Unknown error";
        setError(`Backend Error ${err.response.status}: ${backendMessage}`);
      } else if (err.request) {
        setError(
          "Unable to connect to the backend. Please ensure the backend is running."
        );
      } else {
        setError(err.message);
      }
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e) => {
    if ((e.metaKey || e.ctrlKey) && e.key === "Enter") {
      rankCandidates();
    }
  };

  return (
    <div className={`app ${darkMode ? "dark" : "light"}`}>
      <div className="container">

        <div className="header">
          <div>
            <h1>AI Recruiter System</h1>
            <p className="subtitle">
              Intelligent Candidate Ranking Platform
            </p>
          </div>

          <button
            className="theme-btn"
            onClick={() => setDarkMode(!darkMode)}
          >
            {darkMode ? "☀ Light" : "🌙 Dark"}
          </button>
        </div>

        <div className="input-card">
          <h2>Job Description</h2>

          <textarea
            placeholder="Paste the job description here..."
            value={jobDescription}
            onChange={(e) => setJobDescription(e.target.value)}
            onKeyDown={handleKeyDown}
          />

          <div className="controls">
            <div className="control-group">
              <label htmlFor="topK">Results</label>
              <input
                id="topK"
                type="number"
                min="1"
                max="20"
                value={topK}
                onChange={(e) => setTopK(e.target.value)}
              />
            </div>

            <label className="llm-toggle">
              <input
                type="checkbox"
                checked={useLlm}
                onChange={(e) => setUseLlm(e.target.checked)}
              />
              Use AI skill extraction
            </label>

            <button
              className="rank-btn"
              onClick={rankCandidates}
              disabled={loading}
            >
              {loading ? "Ranking Candidates..." : "Rank Candidates"}
            </button>
          </div>
        </div>

        {loading && (
          <div className="loading">
            <h3>🤖 AI is evaluating candidates...</h3>
            <p>This may take a few seconds.</p>
          </div>
        )}

        {error && (
          <div className="error">
            {error}
          </div>
        )}

        {!loading && !error && results.length === 0 && (
          <div className="empty">
            <h2>🤖 Welcome</h2>
            <p>
              Paste a job description and click
              <strong> Rank Candidates </strong>
              to find the best matching candidates.
            </p>
          </div>
        )}

        {results.length > 0 && (
          <>
            <h2 className="results-title">
              Top {results.length} Matching Candidates
            </h2>

            <div className="results-grid">
              {results.map((candidate) => (
                <div
                  className="card"
                  key={candidate.candidate_id}
                >
                  <div className="card-top">
                    <h3>
                      {candidate.current_title || "Unknown Title"}
                    </h3>

                    <span className="score">
                      {Number(candidate.final_score || 0).toFixed(2)}
                    </span>
                  </div>

                  <p>
                    <strong>ID:</strong>{" "}
                    {candidate.candidate_id}
                  </p>

                  <p>
                    <strong>Experience:</strong>{" "}
                    {candidate.years_experience ?? 0} years
                  </p>

                  <p>
                    <strong>Location:</strong>{" "}
                    {candidate.location || "N/A"}
                  </p>

                  <div className="score-breakdown">
                    <span title="How well skills match the job description">
                      JD match: {Number(candidate.jd_score ?? 0).toFixed(0)}%
                    </span>
                    <span title="Candidate's overall profile strength">
                      Profile: {Number(candidate.profile_score ?? 0).toFixed(0)}
                    </span>
                  </div>

                  {candidate.matched_skills?.length > 0 && (
                    <div className="skills">
                      {candidate.matched_skills.map((skill, index) => (
                        <span key={`m-${index}`} className="skill skill-matched">
                          ✓ {skill}
                        </span>
                      ))}
                    </div>
                  )}

                  {candidate.missing_skills?.length > 0 && (
                    <div className="skills">
                      {candidate.missing_skills.map((skill, index) => (
                        <span key={`x-${index}`} className="skill skill-missing">
                          {skill}
                        </span>
                      ))}
                    </div>
                  )}

                  {(!candidate.matched_skills?.length && !candidate.missing_skills?.length) && (
                    <div className="skills">
                      {candidate.skill_names?.length ? (
                        candidate.skill_names
                          .slice(0, 8)
                          .map((skill, index) => (
                            <span key={index} className="skill">
                              {skill}
                            </span>
                          ))
                      ) : (
                        <span className="skill">No skills available</span>
                      )}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </>
        )}

      </div>
    </div>
  );
}

export default App;