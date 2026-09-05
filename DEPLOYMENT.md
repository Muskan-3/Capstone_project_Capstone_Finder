# Deploying Capstone Compass

Split deployment: **frontend → Vercel**, **backend → Render**. Vercel's
serverless functions have no persistent filesystem, and this backend needs
one (a SQLite file + trained model artifacts on disk), so the two halves live
on different platforms and talk over HTTPS.

```
Browser → Vercel (Next.js, static + SSR)  →  Render (FastAPI, persistent disk)
```

Total cost: **$0** on the free tier of both, with one caveat below.

---

## 1 · Backend → Render

1. Go to [dashboard.render.com](https://dashboard.render.com) → **New +** → **Web Service** → connect the `Capstone_project_Capstone_Finder` GitHub repo.
   *(If you connect the repo and Render offers "Apply Blueprint" because it found `render.yaml` at the root, that pre-fills everything below — check it matches, then skip to step 2.)*
2. Configure the service:
   | Field | Value |
   |---|---|
   | Root Directory | `backend` |
   | Runtime | Python 3 |
   | Build Command | `pip install -r requirements.txt` |
   | Start Command | `uvicorn app.main:app --host 0.0.0.0 --port $PORT` |
   | Health Check Path | `/api/health` |
   | Instance Type | Free |
3. **Add a persistent disk** (Settings → Disks → Add Disk) — without this, the database and every retrained model are wiped on each redeploy:
   | Field | Value |
   |---|---|
   | Name | `compass-data` |
   | Mount Path | `/var/data` |
   | Size | 1 GB |
4. **Environment variables** (Settings → Environment):
   | Key | Value |
   |---|---|
   | `COMPASS_DATABASE_URL` | `sqlite:////var/data/compass.db` |
   | `COMPASS_ARTIFACTS_DIR` | `/var/data/artifacts` |
   | `COMPASS_AUTO_SEED` | `true` |
   | `COMPASS_CORS_ORIGINS` | `http://localhost:3000` *(update after step 2 below)* |
   | `COMPASS_CORS_ORIGIN_REGEX` | `https://.*\.vercel\.app` *(covers every preview deployment)* |
5. Deploy. First boot seeds the database from `backend/data/source.xlsx` and trains model v1 automatically (watch the logs for `trained model v1: k=6, ...`). Every boot after that reuses the disk and skips reseeding.
6. Copy the service URL Render gives you, e.g. `https://capstone-compass-api.onrender.com`. Confirm it works: `curl https://<your-service>.onrender.com/api/health`.

**Free-tier caveat:** Render's free web services spin down after 15 minutes idle. The next request wakes it up but takes 30–60s (a Python cold start). Fine for a demo; if that first-load delay matters, upgrade the Render service to a paid instance (no code changes needed) — it's the same deploy either way.

---

## 2 · Frontend → Vercel

1. Go to [vercel.com/new](https://vercel.com/new) → import the same GitHub repo.
2. Set **Root Directory** to `frontend`. Vercel auto-detects Next.js — no other build settings needed.
3. Add an environment variable before the first deploy:
   | Key | Value |
   |---|---|
   | `NEXT_PUBLIC_API_BASE` | `https://<your-render-service>.onrender.com` (from step 1.6, **no trailing slash**) |
4. Deploy. Vercel gives you a URL like `https://capstone-compass.vercel.app`.

`NEXT_PUBLIC_*` variables are baked in at build time and shipped to the browser - if you change this later, you must **redeploy** the frontend (not just restart) for it to take effect.

---

## 3 · Close the loop: tell the backend about the frontend

Go back to Render → your service → Environment → update:

```
COMPASS_CORS_ORIGINS=http://localhost:3000,https://capstone-compass.vercel.app
```

(the `COMPASS_CORS_ORIGIN_REGEX` from step 1.4 already covers Vercel's per-branch preview URLs, so only the production domain needs adding here). Save - Render restarts the service automatically. That's it: open the Vercel URL and it should reach the API.

---

## Verifying it worked

```bash
curl https://<your-render-service>.onrender.com/api/health
curl https://<your-render-service>.onrender.com/api/model/status
```

Then open the Vercel URL, sign in, and send a chat message. If the browser console shows a CORS or network error, double-check `NEXT_PUBLIC_API_BASE` (frontend) and `COMPASS_CORS_ORIGINS` (backend) match exactly - including `https://` and no trailing slash.

## What doesn't change

Everything else about the app is identical to running it locally: same
database schema, same ML pipeline, same admin panel at `/admin` on the
deployed frontend (talking to the deployed backend), same offline
guarantee - there is still no hosted LLM anywhere in this path, just a
FastAPI process that now happens to live on Render instead of your laptop.

## Later: swapping in Supabase

If you move the student database to Supabase (see `frontend/lib/supabase.ts`),
Render's persistent disk is only needed for the trained model artifacts at
that point - worth revisiting whether the backend needs a disk at all, or can
retrain in memory on boot from the corpus in Supabase. Ask when you're ready
to make that change; it's a backend-side swap, not something Vercel affects.
