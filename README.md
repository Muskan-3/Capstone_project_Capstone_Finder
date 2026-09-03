# Capstone Compass

A full-stack, **fully offline** recommender that charts final-year capstone problem
statements against a student's skills and interests, using classical ML
(TF-IDF → KMeans clustering → cosine ranking → MMR diversification).

- **No hosted LLM.** No OpenAI / Anthropic / any inference API.
- **No runtime model downloads.** `scikit-learn`'s `TfidfVectorizer` learns its
  vocabulary from *this* corpus. Fonts are vendored as `.woff2`.
- **Degrades honestly.** A profile with no close cluster gets an explicit
  low-confidence result with real scores, never a forced quantum match.
- **Grounded.** Every recommendation cites a real `project_id` and its real
  cosine similarity. The shown text is the real problem statement wrapped in a
  fixed rationale template — nothing is generated.

```
FinalYearCapstoneProject/
├── backend/     FastAPI + SQLite + scikit-learn pipeline
└── frontend/    Next.js 14 (App Router) + TypeScript + Tailwind
```

---

## Quick start

Two terminals. Backend first (it seeds itself on first run).

### 1 · Backend  → http://127.0.0.1:8000

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# First run auto-ingests backend/data/source.xlsx and trains model v1.
uvicorn app.main:app --port 8000
```

Interactive API docs: http://127.0.0.1:8000/docs

### 2 · Frontend  → http://localhost:3000

```bash
cd frontend
npm install
npm run dev
```

If the backend is not on port 8000, set `NEXT_PUBLIC_API_BASE` in
`frontend/.env.local` (see `.env.local.example`).

---

## Verifying it works (Section 11 / 12 of the brief)

Run these from `backend/` with the venv active.

| Check | Command | Expected |
|---|---|---|
| Ingestion flags the dirty rows, never crashes | `python -m scripts.ingest_report` | 200 rows parsed, 13 flagged (1 duplicate ID + 4 missing-title + 7 missing-statement — see `DATA_NOTES.md` for why this differs from the brief's 1/2/4) |
| Pipeline routes sensibly; non-quantum is **not** force-matched | `python -m scripts.pipeline_demo` | web-dev profile → `mode: low_confidence`; quantum profile → `mode: routed` |
| Full API contract + guardrails | `pytest -q` | 18 passed |
| End-to-end against a running server | `python -m scripts.api_smoke http://127.0.0.1:8000` | ALL PASSED |

---

## Architecture

### Backend (`backend/app/`)

| Module | Responsibility |
|---|---|
| `ml/ingest.py` | Read xlsx/csv, discover the header row, apply the Section 3 cleaning rules, produce a flag report. Handles the initial workbook and later uploaded batches identically. |
| `ml/pipeline.py` | Fit `TfidfVectorizer(max_features=5000, ngram_range=(1,2), stop_words="english")`, sweep KMeans `k ∈ [4,10]` and keep the best cosine **silhouette**, label clusters by their top TF-IDF terms, package everything into a versioned `ModelArtifacts`. |
| `ml/recommender.py` | Route a student vector to a cluster (or the honest low-confidence state), rank by `0.8·relevance + 0.2·feasibility + 0.0·faculty`, diversify the top 5 with **MMR (λ=0.7)**, build the `Explain this match` payload, wrap the real statement in the rationale template. Also the rule-based refinement parser. |
| `ml/store.py` | Persist / load artifacts as `artifacts/v{n}/model.joblib`. Old versions are never deleted. |
| `training.py` | Glue: read the active pool from SQLite → `train()` → `save()` → write cluster ids back → flip `model_versions.is_active`. |
| `routers/` | The Section 6 endpoints. |

### The scoring formula (shown verbatim in the UI)

```
composite = 0.80·relevance + 0.20·feasibility + 0.00·faculty_match

relevance      = cosine(student TF-IDF, statement TF-IDF) / 0.50, capped at 1
                 (fixed scale ⇒ the dial can never read "full / perfect")
feasibility    = length-based scoping proxy:
                 <120 → 0.70, <250 → 0.85, 250–900 → 1.00, 900–1400 → 0.92, >1400 → 0.80
faculty_match  = 0  (feature built, inactive until real preference data exists)
```

Routing threshold, weights, MMR λ, and the confidence bands are all in
`app/config.py` and overridable via `COMPASS_*` env vars — no code changes needed.

### Frontend (`frontend/app/`)

`/` landing · `/onboarding` profile form · `/recommendations` the two-pane
workspace (instrument panel + flowing card list + plain-language refine bar) ·
`/admin` corpus browser, Needs-Review queue, batch upload, retrain + version
history, faculty-preference form · `/about` how it works + standing disclosures.

Design tokens (palette, type) live once in `app/globals.css` + `tailwind.config.ts`.
The one deliberate motion moment is the match-compass needle settling; it is
skipped under `prefers-reduced-motion`.

---

## Retraining with a new batch (no code)

Admin → **Model & batches** → *Upload a new batch* (`.xlsx`/`.csv` with
`ProjectID`, `Title`, `Problem Statement` columns) → the Section 3 cleaning rules
run automatically and rows are tagged with a `source_batch` → **Retrain now**
re-runs the whole pipeline over the entire active pool, writes a new
`model_versions` row and makes it live. Previous versions stay for one-click
rollback.
