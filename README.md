# TalentMatch

A small, fully-working resume-to-job matching application, built as a portfolio
project for a Python Developer / AI Engineer interview.

You upload a candidate's resume (PDF) and paste a job description. TalentMatch
extracts structured data from both with an LLM, calculates a **transparent,
deterministic match score in plain Python**, and asks the LLM to explain that
score in plain English.

---

## 1. Overview

**Flow:**

```
PDF resume ──▶ text extraction (pdfplumber) ──▶ LLM structured extraction ──▶ ResumeData
Job description text ─────────────────────────▶ LLM structured extraction ──▶ JobRequirements

ResumeData + JobRequirements ──▶ Python scoring engine ──▶ MatchResult (score + breakdown)
MatchResult ──▶ LLM explanation (phrasing only, no scoring) ──▶ final response
```

The LLM is used for **information extraction** and **natural-language
explanation**. It never decides the final number — that's Python's job, and
that separation is the main design decision this project demonstrates.

---

## 2. Architecture

```
talentmatch/
  backend/
    app/
      main.py                 FastAPI app, CORS, routers, global error handler
      config.py                Settings (.env) via pydantic-settings
      routes/
        resume.py              POST /resume/upload
        match.py                POST /match, POST /analyze-resume
      services/
        pdf_extractor.py        PDF -> raw text (pdfplumber)
        llm_service.py          All OpenAI calls (extraction + explanation)
        errors.py                Domain-specific exceptions
      models/
        schemas.py               Pydantic request/response/domain models
      matching/
        scorer.py                 Deterministic scoring engine (pure Python)
    requirements.txt
    .env.example

  frontend/
    src/
      components/
        ResumeUpload.jsx
        JobDescriptionInput.jsx
        MatchResults.jsx
      services/
        api.js                    fetch wrappers for the backend API
      App.jsx                     Page state + orchestration
      App.css
    package.json
    vite.config.js
```

**Layering rationale:**
- `routes/` only translates HTTP ↔ domain calls and maps exceptions to status codes.
- `services/` and `matching/` contain the actual logic and have no FastAPI dependency — they could be reused in a CLI or a batch job.
- `models/schemas.py` is the single source of truth for every shape of data moving through the app, used both for API contracts *and* for validating what the LLM returns.

---

## 3. Matching approach

The overall score is a weighted sum of four independently-calculated components:

| Component            | Weight | How it's calculated |
|-----------------------|--------|----------------------|
| Skills                | 50%    | `required_skills` matched (80% of this component) + `preferred_skills` matched (20%), as a ratio of skills found in the candidate's skill list |
| Experience            | 25%    | 100 if candidate years ≥ required years, otherwise a proportional partial score (`candidate / required * 100`) |
| Job title relevance   | 15%    | Ratio of meaningful job-title keywords found anywhere in the resume text |
| Location              | 10%    | 100 if the job's stated location string appears in the resume text, else 0; neutral (100) if the job has no location |

All of this lives in `backend/app/matching/scorer.py` as plain, testable
Python functions with no LLM calls — see [section 8](#8-why-the-score-is-calculated-in-python-instead-of-by-the-llm)
for why.

---

## 4. Technologies

- **Backend:** Python, FastAPI, Pydantic v2, pydantic-settings, pdfplumber, OpenAI SDK, uvicorn
- **Frontend:** React 18, Vite, plain CSS (no UI framework, to keep the project easy to read and explain)
- **LLM:** OpenAI Chat Completions API with `response_format: json_object` for structured extraction

---

## 5. Setup instructions

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
# then edit .env and set OPENAI_API_KEY=sk-...

uvicorn app.main:app --reload   # runs on http://localhost:8000
```

Visit `http://localhost:8000/docs` for interactive Swagger API docs.

### Frontend

```bash
cd frontend
npm install
npm run dev                     # runs on http://localhost:5173
```

The frontend calls the backend at `http://localhost:8000` by default. To
override, create `frontend/.env` with:

```
VITE_API_BASE=http://localhost:8000
```

---

## 6. API documentation

### `POST /resume/upload`
Upload a PDF resume. Extracts text, then runs LLM extraction on it.

- **Body:** `multipart/form-data`, field `file` (PDF)
- **200 response:**
  ```json
  {
    "resume_text": "raw extracted text...",
    "resume": {
      "name": "Jane Doe",
      "email": "jane@example.com",
      "phone": "555-123-4567",
      "skills": ["Python", "FastAPI"],
      "experience_years": 4,
      "education": ["B.Tech Computer Science"],
      "raw_text_length": 812
    }
  }
  ```
- **Errors:** `400` invalid file/PDF, `422` empty resume text, `500` missing API key, `502` LLM failure

### `POST /analyze-resume`
Run just the resume-extraction step on already-extracted text (useful if the
frontend already has the text and doesn't want to re-upload the file).

- **Body:** `{ "resume_text": "..." }`
- **200 response:** `{ "resume": { ...ResumeData } }`

### `POST /match`
Full pipeline: extract resume + job requirements, score, explain.

- **Body:**
  ```json
  { "resume_text": "...", "job_description": "..." }
  ```
- **200 response:**
  ```json
  {
    "resume": { "...ResumeData" },
    "job": { "...JobRequirements" },
    "match": {
      "overall_score": 81.66,
      "skills": { "matched_required": ["Python", "FastAPI"], "missing_required": ["AWS"], "matched_preferred": ["Docker"], "missing_preferred": [], "skill_score": 63.33 },
      "experience": { "candidate_years": 4, "required_years": 3, "meets_requirement": true, "experience_score": 100 },
      "title": { "candidate_signal": "Found title keywords in resume: backend, python, developer", "job_title": "Backend Python Developer", "title_score": 100 },
      "location": { "candidate_location": "Bangalore", "job_location": "Bangalore", "matches": true, "location_score": 100 },
      "explanation": "Strong match on core backend skills; missing AWS experience."
    }
  }
  ```
- **Errors:** `422` empty resume/job description, `500` missing API key, `502` LLM failure

### `GET /health`
Returns `{ "status": "ok", "llm_configured": true|false }` — useful to check the API key is picked up without spending a request.

---

## 7. Example input/output

**Input resume text (excerpt):**
```
Jane Doe
jane.doe@example.com | 555-123-4567
SKILLS
Python, FastAPI, React, Docker, PostgreSQL
EXPERIENCE
Backend Python Developer, XYZ Corp, Bangalore, 2021-2025 (4 years)
EDUCATION
B.Tech Computer Science, ABC University
```

**Input job description (excerpt):**
```
Looking for a Backend Python Developer.
Required: Python, FastAPI, AWS.
Preferred: Docker.
3+ years experience. Location: Bangalore.
```

**Output (`overall_score: 86.66`):** matched required skills `Python, FastAPI`,
missing `AWS`; experience requirement met (4 ≥ 3 years); title and location
both match, since "Backend Python Developer" and "Bangalore" both appear in
the resume text.

This example was verified against the actual scoring code during development
(see section 9).

---

## 8. Why the score is calculated in Python instead of by the LLM

This is the single most important design decision in the project, so it's
worth stating explicitly:

1. **Reproducibility.** The same resume and job description must always
   produce the same score. LLM output is inherently non-deterministic (even
   at `temperature=0` it isn't perfectly stable across model versions),
   which makes a purely LLM-generated score untrustworthy for something as
   consequential as a hiring decision.
2. **Explainability.** Every number in `MatchResult` traces back to a line of
   arithmetic in `scorer.py` that can be logged, unit tested, and shown to a
   recruiter or auditor. An LLM-generated score is a black box even if it
   "looks" reasonable.
3. **Fairness / auditability.** Deterministic scoring means the same rules
   apply to every candidate, and the weighting (50/25/15/10) is a documented,
   inspectable business decision rather than something buried in a prompt.
4. **Cost and latency.** Arithmetic is free and instant; it doesn't need a
   model call.

The LLM is still essential — for **turning unstructured text into structured
data** (resume/job parsing) and for **turning a score into a sentence a human
enjoys reading** — but it is kept out of the one place where determinism
actually matters.

---

## 9. Interview preparation

### Q1: Why FastAPI over Flask/Django?
FastAPI gives request/response validation and serialization "for free" via
Pydantic models — the same `ResumeData` and `JobRequirements` models are used
to validate the API's own request bodies *and* to validate what the LLM
returns, so there's one schema to maintain instead of three. It also gives
async support, automatic OpenAPI/Swagger docs (`/docs`), and clear type-hint
based routing, which makes the codebase easier to onboard someone into
quickly — relevant for a project you need to explain in an interview.

### Q2: How does PDF extraction work here?
`pdfplumber` opens the PDF and calls `page.extract_text()` on each page,
joining the results. It reads the text layer that's already embedded in the
PDF; it does **not** do OCR, so a scanned resume with no text layer will
raise a clear `EmptyResumeError` rather than silently returning garbage. For
production use with scanned documents, you'd add an OCR fallback (e.g.
Tesseract or a cloud OCR API) when `extract_text()` comes back empty.

### Q3: Why use an LLM at all, if the scoring is deterministic?
Two reasons the LLM earns its place: (1) resumes and job descriptions are
unstructured, inconsistent free text — regex alone can extract an email or
phone number reasonably well, but reliably pulling out "skills," "years of
experience," or distinguishing "required" vs "preferred" skills from
arbitrary phrasing needs language understanding. (2) After scoring, a
recruiter wants a one-glance sentence, not four separate percentages — the
LLM turns numbers into a readable explanation.

### Q4: Why shouldn't the LLM directly generate the match score?
See section 8 above — determinism, explainability, fairness/auditability,
and cost. In an interview, the crisp one-line version is: *"I don't want a
hiring-relevant number to change if I re-run the same input, or to be
impossible to explain to a candidate who asks why they weren't shortlisted."*

### Q5: How does the scoring system actually work?
Four independent components, each 0–100, combined with fixed weights (skills
50%, experience 25%, title relevance 15%, location 10%). Skills score is a
weighted blend of the required-skill match ratio (80%) and preferred-skill
match ratio (20%). Experience score is 100 if the candidate meets the
minimum, otherwise linear partial credit. Title and location scores are
keyword/substring checks against the resume text, since the resume schema
doesn't have dedicated "current title" or "location" fields. All of this is
in `scorer.py` as small, independently testable functions.

### Q6: How is structured output from the LLM handled and validated?
The OpenAI call uses `response_format={"type": "json_object"}` so the model
is constrained to return valid JSON, and the system prompt spells out the
exact key names and types expected. The raw JSON is then parsed into a
Pydantic model (`ResumeData` / `JobRequirements`); if a field is missing or
the wrong type, Pydantic raises a `ValidationError`, which the service layer
converts into an `InvalidExtractedDataError` and the route turns into a
`422` response. Nothing downstream ever touches unvalidated LLM output.

### Q7: What happens if the OpenAI API key is missing or the call fails?
Missing key raises `MissingAPIKeyError` → `500` with a clear message,
checked before ever calling the API. An API failure during extraction raises
`LLMFailureError` → `502`, since it's an upstream dependency failing, not a
bug in this service. The explanation step specifically is treated as
"best-effort": if it fails, `generate_explanation()` falls back to a
deterministic template built from the score data, so the whole `/match`
request doesn't fail just because the last, non-critical LLM call did.

### Q8: How would you test this without hitting the real OpenAI API in CI?
The service layer is a thin wrapper around the OpenAI client, so
`app.services.llm_service.OpenAI` can be patched with a mock in tests (this
is exactly how the project was verified during development — see the next
question). The scoring engine (`scorer.py`) takes plain Pydantic objects and
has zero network calls, so it's tested directly with no mocking at all.

### Q9: How was this project tested locally?
1. `scorer.py` was unit-tested directly with hand-built `ResumeData`/
   `JobRequirements` objects to confirm the weighted score and each
   sub-score's math.
2. `pdf_extractor.py` was tested against a real generated PDF resume to
   confirm text extraction end-to-end.
3. The FastAPI app was exercised with `TestClient` to confirm routing, CORS,
   and every error path (invalid PDF, wrong content type, missing job
   description, missing API key) returns the right status code and message.
4. The full `/match` pipeline (PDF → LLM extraction → Python scoring → LLM
   explanation) was run with the OpenAI client mocked to return realistic
   structured JSON, confirming the whole pipeline wires together correctly
   without requiring a live API key.
5. The React frontend was built with `npm run build` to confirm it compiles
   cleanly with no runtime import errors.

### Q10: How could this be improved for production?
- Add OCR fallback for scanned/image-only PDF resumes.
- Add proper structured "current title" and "location" fields to resume
  extraction instead of the substring-search fallback used for those two
  score components.
- Add automated tests (pytest) instead of the manual verification scripts
  used during development, plus CI.
- Add authentication, rate limiting, and file-size/type validation hardening
  on the upload endpoint.
- Cache LLM extraction results (e.g. keyed by a hash of the input text) to
  avoid re-paying for identical resumes/job descriptions.
- Support batch matching (one job description against many resumes) with
  background/async processing instead of one-at-a-time synchronous requests.
- Swap the keyword-based title/location scoring for a more robust approach
  (e.g. geocoding for location, embedding similarity for title relevance).
