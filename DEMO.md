# Demo walkthrough (~5 minutes)

Start both servers (see `README.md`). Backend on :8000, frontend on :3000.

## 0 · Framing (30s)

> "The pitch isn't a bigger model — it's a grounded one. Everything here runs on
> our own 200 statements, offline, with visible reasoning and honest uncertainty."

## 1 · Landing → the honest disclosure (30s)

Open **http://localhost:3000**. Read the *"What this tool will and won't claim"*
card aloud — real Project IDs, real scores, no perfect match, tells you when it
doesn't know.

## 2 · Onboard a quantum-leaning student (45s)

**Start** → fill in:

- Name: `Priya Nair`
- Skills: `Python`, `Qiskit`, `linear algebra`, `PennyLane`
- Interests: `quantum machine learning`, `variational circuits`, `optimization`
- Comfort: **Fluent**
- Prior projects: *"Built a variational quantum classifier for small image datasets."*

**Take a bearing.**

## 3 · The workspace (90s)

- The **match compass** needle settles once (the one deliberate animation).
- Left **instrument panel**: routing confidence ≈ `0.19`, and *"Bearing to each
  domain cluster"* shows it routed into the quantum-ML clusters.
- Top card is brass-edged (primary). Expand **Explain this match**: real cosine
  number, the length-based feasibility proxy with the actual char count, and a
  bar chart of *which of your terms drove it* (`variational`, `optimization`…).
- Every card shows a monospace **Project ID** you could look up.

Then in the **refine bar** at the bottom type:

> `show me more optimization ideas, avoid AR/VR and simulation`

The banner reports what it excluded/boosted; the ranking re-computes.

## 4 · The honest failure mode (45s)

**Start** → new profile:

- Name: `Sam Okafor`
- Skills: `React`, `TypeScript`, `Node.js`, `PostgreSQL`
- Interests: `web applications`, `developer tools`, `accessibility`

**Take a bearing.** → The workspace shows a **Low Confidence** banner:

> *"We don't have enough matching problem statements in your area yet… showing
> the closest available with their real similarity scores. Treat these as weak
> leads."*

This is the core point: no forced quantum match, scores shown honestly.

## 5 · Admin — the review process + retraining (60s)

**Admin**:

- **Needs review**: exactly the 13 flagged rows (1 duplicate ID → suffixed `-B`,
  4 missing titles incl. the ones titled `v` / `uu`, 7 missing/echoed
  statements). Expand one, add a title, **Save** — it clears the flag.
- **Model & batches**: upload `backend/tests/fixtures/next_batch.csv` (or any
  xlsx/csv with the right columns) → **Retrain now** → a new version appears,
  active; the previous one stays with a **Roll back to this** button.
- **Faculty preferences**: the banner states plainly it's inactive; you can add
  a row but it stays weighted 0.

## 6 · About (30s)

Plain-language TF-IDF + KMeans explanation, live corpus counts, and the five
standing disclosures.
