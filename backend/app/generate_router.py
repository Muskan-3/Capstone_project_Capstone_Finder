"""Offline project-idea generator - the chatbot's Generate mode.

Ideas are composed from curated, internally-consistent seeds (idea_bank.py), never
pulled from the corpus, and never carry a Project ID. Each idea gets a novelty
score: 1 - its highest cosine similarity to any active corpus statement, using the
active model's TF-IDF vectorizer read-only. Near-copies of existing statements are
dropped. No LLM, no network, no extra dependencies.

    GET  /api/generate/options   -> domains (+ keywords) and levels
    POST /api/generate           -> {domain, level, count, interests, seed}
"""

from __future__ import annotations

import random
import re
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sklearn.preprocessing import normalize
from sqlalchemy.orm import Session

from .db import get_db
from .idea_bank import DEFAULT_LEVEL, DOMAINS, GENERATED_LABEL, LEVELS, scope
from .ml.pipeline import ModelArtifacts
from .training import get_active_artifacts

router = APIRouter(prefix="/api/generate", tags=["generate"])

# an idea this close to an existing statement is a paraphrase, not a new idea
MIN_NOVELTY = 0.35
_WORD = re.compile(r"[a-z0-9]+")
_STOP = {"a", "an", "the", "and", "or", "for", "on", "in", "of", "to", "with", "me", "some",
         "ideas", "idea", "project", "projects", "new", "give", "generate", "create", "about",
         "related", "please", "can", "you", "i", "want", "need", "few", "topics", "topic"}


class GenerateRequest(BaseModel):
    domain: str
    level: str = DEFAULT_LEVEL
    count: int = Field(default=3, ge=1, le=5)
    interests: str = Field(default="", max_length=400)  # free text to steer seed choice
    seed: int | None = None                             # for reproducible output


class GenerateResponse(BaseModel):
    domain: str
    level: str
    label: str
    ideas: list[dict[str, Any]]
    note: str


# --------------------------------------------------------------------------- #
# mapping helpers (used by the chat endpoint too)
# --------------------------------------------------------------------------- #
def map_domain(text: str) -> str | None:
    """Pick the domain whose keywords best match the text; None if nothing matches."""
    low = (text or "").lower()
    best, best_score = None, 0
    for name, d in DOMAINS.items():
        score = sum(
            len(kw) for kw in d["keywords"]
            if re.search(rf"(?<![a-z0-9]){re.escape(kw)}(?![a-z0-9])", low)
        )
        if score > best_score:
            best, best_score = name, score
    return best


def map_level(text: str) -> str:
    low = (text or "").lower()
    if re.search(r"\b(beginner|easy|simple|basic|first[- ]year)\b", low):
        return "Beginner"
    if re.search(r"\b(advanced|hard|challenging|complex|research)\b", low):
        return "Advanced"
    return DEFAULT_LEVEL


def _canonical_domain(name: str) -> str | None:
    for d in DOMAINS:
        if d.lower() == (name or "").strip().lower():
            return d
    return map_domain(name)


# --------------------------------------------------------------------------- #
# core
# --------------------------------------------------------------------------- #
def _novelty(art: ModelArtifacts | None, text: str) -> float | None:
    if art is None:
        return None
    vec = normalize(art.vectorizer.transform([text]))
    if vec.nnz == 0:
        return 1.0
    max_sim = float((art.doc_matrix @ vec.T).max())
    return round(max(0.0, 1.0 - max_sim), 3)


def generate_ideas(
    art: ModelArtifacts | None,
    domain: str,
    level: str = DEFAULT_LEVEL,
    count: int = 3,
    interests: str = "",
    seed: int | None = None,
) -> list[dict[str, Any]]:
    spec = DOMAINS[domain]
    rng = random.Random(seed)
    want = {w for w in _WORD.findall(interests.lower()) if w not in _STOP and len(w) > 2}

    candidates = []
    for task, problem, methods, contexts in spec["seeds"]:
        seed_words = set(_WORD.findall(" ".join([task, problem, *methods,
                                                  *(c[1] for c in contexts)]).lower()))
        relevance = len(want & seed_words)
        for method in methods:
            for ctx_label, ctx_phrase in contexts:
                title = f"{task} for {ctx_label}"
                description = (f"{problem} This project uses {method} for {ctx_phrase}. "
                               f"{scope(spec['kind'], level)}")
                novelty = _novelty(art, f"{title} {description}")
                if novelty is not None and novelty < MIN_NOVELTY:
                    continue
                candidates.append((relevance, rng.random(), task, title, description, novelty))

    # most relevant to the user's words first, random among ties; one idea per seed
    candidates.sort(key=lambda c: (-c[0], c[1]))
    ideas, used = [], set()
    for relevance, _, task, title, description, novelty in candidates:
        if task in used:
            continue
        used.add(task)
        ideas.append({
            "title": title,
            "description": description,
            "domain": domain,
            "level": level,
            "novelty": novelty,
            "label": GENERATED_LABEL,
        })
        if len(ideas) == count:
            break
    return ideas


# --------------------------------------------------------------------------- #
# routes
# --------------------------------------------------------------------------- #
@router.get("/options")
def options() -> dict[str, Any]:
    return {
        "domains": [{"name": n, "keywords": d["keywords"]} for n, d in DOMAINS.items()],
        "levels": list(LEVELS),
        "default_level": DEFAULT_LEVEL,
    }


@router.post("", response_model=GenerateResponse)
def generate(payload: GenerateRequest, db: Session = Depends(get_db)) -> GenerateResponse:
    domain = _canonical_domain(payload.domain)
    if domain is None:
        raise HTTPException(422, f"unknown domain {payload.domain!r}; "
                                 f"choose one of: {', '.join(DOMAINS)}")
    level = next((lv for lv in LEVELS if lv.lower() == payload.level.strip().lower()), None)
    if level is None:
        raise HTTPException(422, f"unknown level {payload.level!r}; choose one of: {', '.join(LEVELS)}")

    art = get_active_artifacts(db)
    ideas = generate_ideas(art, domain, level, payload.count, payload.interests, payload.seed)
    note = ("Novelty = 1 - highest cosine similarity to any statement in the catalogue "
            "(1.0 = nothing similar exists)."
            if art is not None else "No active model, so novelty could not be measured.")
    return GenerateResponse(domain=domain, level=level, label=GENERATED_LABEL, ideas=ideas, note=note)
