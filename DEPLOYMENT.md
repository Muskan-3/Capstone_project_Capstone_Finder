# Deploying Capstone Compass

Split deployment: **frontend → Vercel**, **backend → Render**, **database →
Supabase (Postgres)**. The backend's ML dependencies (scikit-learn + scipy +
numpy, ~265MB) exceed Vercel's 250MB serverless function limit, and its
persistent state (student data, chat history, every trained model) needs a
real database, not a request-scoped filesystem — so it runs as a normal
long-lived process on Render instead, talking to Postgres.

```
Browser → Vercel (Next.js)  →  Render (FastAPI, one persistent process)  →  Supabase (Postgres)
```

Cost: **$0** on the free tier of all three, with one caveat below.

---

## 0 · Database → Supabase

1. Create a project at [supabase.com](https://supabase.com/dashboard) (free tier).
2. Project Settings → Database → **Connection string** → copy the **Session pooler** URI (not "Direct connection" - the pooler survives Render's network setup more reliably). It looks like:
   ```
   postgresql://postgres.xxxxxxxxxxxx:[YOUR-PASSWORD]@aws-0-<region>.pooler.supabase.com:5432/postgres
   ```
3. Replace `[YOUR-PASSWORD]` with your database password (set when you created the project). Keep this string handy for step 1.4 below - it's a secret, never commit it to the repo.

Nothing else to do here - the app creates its own tables on first boot.

---

## 1 · Backend → Render

1. [dashboard.render.com](https://dashboard.render.com) → **New +** → **Web Service** → connect the GitHub repo.
   *(If Render offers "Apply Blueprint" because it found `render.yaml` at the repo root, that pre-fills everything below except the database URL secret - check it, then skip to step 4.)*
2. Configure the service:
   | Field | Value |
   |---|---|
   | Root Directory | `backend` |
   | Runtime | Python 3 |
   | Build Command | `pip install -r requirements.txt` |
   | Start Command | `uvicorn app.main:app --host 0.0.0.0 --port $PORT` |
   | Health Check Path | `/api/health` |
   | Instance Type | Free |
3. No disk needed - skip straight to environment variables.
4. **Environment variables** (Settings → Environment):
   | Key | Value |
   |---|---|
   | `COMPASS_DATABASE_URL` | the Supabase connection string from step 0.2, with `postgresql://` changed to `postgresql+psycopg2://` |
   | `COMPASS_AUTO_SEED` | `true` |
   | `COMPASS_CORS_ORIGINS` | `http://localhost:3000` *(update after step 2 below)* |
   | `COMPASS_CORS_ORIGIN_REGEX` | `https://.*\.vercel\.app` *(covers every Vercel preview deployment)* |
5. Deploy. First boot seeds Supabase from `backend/data/source.xlsx` and trains model v1 - watch the logs for `trained model v1: k=6, ...`. Every boot after that finds existing rows and skips reseeding, exactly like local dev.
6. Copy the service URL Render gives you, e.g. `https://capstone-compass-api.onrender.com`. Confirm: `curl https://<your-service>.onrender.com/api/health`.

**Free-tier caveat:** Render's free web services spin down after 15 minutes idle; the next request wakes it in 30-60s. Fine for a demo; upgrading to a paid instance removes it with no code changes.

---

## 2 · Frontend → Vercel

1. [vercel.com/new](https://vercel.com/new) → import the same GitHub repo.
2. Set **Root Directory** to `frontend`. Vercel auto-detects Next.js.
3. Add an environment variable before the first deploy:
   | Key | Value |
   |---|---|
   | `NEXT_PUBLIC_API_BASE` | `https://<your-render-service>.onrender.com` (from step 1.6, no trailing slash) |
4. Deploy → you get a URL like `https://capstone-compass.vercel.app`.

`NEXT_PUBLIC_*` variables are baked in at build time - changing this later requires a **redeploy**, not just a restart.

---

## 3 · Close the loop

Render → your service → Environment → update:

```
COMPASS_CORS_ORIGINS=http://localhost:3000,https://capstone-compass.vercel.app
```

(`COMPASS_CORS_ORIGIN_REGEX` already covers every Vercel preview URL, so only the production domain needs adding here). Save - Render restarts automatically.

---

## Verifying it worked

```bash
curl https://<your-render-service>.onrender.com/api/health
curl https://<your-render-service>.onrender.com/api/model/status
```

Then open the Vercel URL, sign in, and send a chat message. A CORS or
network error in the browser console means `NEXT_PUBLIC_API_BASE` (frontend)
and `COMPASS_CORS_ORIGINS` (backend) don't match exactly - check `https://`
and trailing slashes on both sides.

## What doesn't change

Same database schema, same ML pipeline, same admin panel at `/admin`, same
offline guarantee - there is still no hosted LLM anywhere in this path.
Locally, `pip install -r requirements.txt && uvicorn app.main:app` still
works with zero setup (SQLite, no Supabase account needed) - `COMPASS_DATABASE_URL`
only needs to point at Postgres in the deployed environment.

## Why not "everything on Vercel"

Two independent, unrelated blockers rule it out for this backend specifically:

1. **No persistent disk.** Every serverless invocation gets a throwaway
   filesystem, so a local SQLite file or on-disk model artifacts would not
   survive between requests. Solved by moving all state (including trained
   models - see `model_versions.artifact_blob`) into Postgres, which is
   already done and works the same way in every environment.
2. **Function size.** scikit-learn + scipy + numpy alone total roughly
   265MB, over Vercel's 250MB serverless function limit - this is a
   dependency-footprint problem, not a persistence problem, and the only way
   around it is dropping scikit-learn/scipy for a hand-rolled TF-IDF +
   KMeans in raw numpy, which is a real rewrite of the ML core, not a
   deploy-config change.

If you want to revisit this later (e.g. after slimming the ML dependencies),
the Postgres migration already removes blocker #1 - only #2 would still need
solving.
