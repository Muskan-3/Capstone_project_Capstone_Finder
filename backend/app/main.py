"""Capstone Compass API.

Offline by construction: no API keys, no outbound calls, no model downloads.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func, select

from .config import settings
from .db import SessionLocal, init_db
from .models import ProblemStatement
from .routers import corpus, faculty, feedback, model, recommendations, students

log = logging.getLogger("compass")


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    if settings.auto_seed:
        db = SessionLocal()
        try:
            empty = (db.scalar(select(func.count()).select_from(ProblemStatement)) or 0) == 0
        finally:
            db.close()
        if empty:
            log.warning("empty database - running first-time seed + train from %s",
                        settings.source_workbook)
            from .seed import seed

            try:
                seed()
            except Exception:  # noqa: BLE001 - never let seeding crash startup silently
                log.exception("auto-seed failed; start the API and seed manually")
    yield


app = FastAPI(
    title="Capstone Compass API",
    version="1.0.0",
    description=(
        "Retrieval + ranking over the department's own problem-statement catalogue "
        "using TF-IDF + KMeans + cosine similarity. No hosted LLM, no runtime downloads."
    ),
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_origin_regex=settings.cors_origin_regex,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

for r in (students, recommendations, corpus, model, feedback, faculty):
    app.include_router(r.router)


@app.get("/api/health", tags=["meta"])
def health() -> dict[str, object]:
    return {
        "status": "ok",
        "offline": True,
        "faculty_matching_active": False,
        "notes": "recommendations are retrieval + adaptation over the local corpus, not generative",
    }
