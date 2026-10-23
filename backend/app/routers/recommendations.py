from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from sqlalchemy import select

from ..config import settings
from ..db import get_db
from ..generate_router import generate_ideas, map_domain, map_level
from ..idea_bank import DOMAINS, GENERATED_LABEL
from ..ml.recommender import RecResult, StudentProfile, recommend, refine
from ..models import ProblemStatement, Recommendation, Student
from ..schemas import RecommendationRequest, RecommendationResponse, RefineRequest
from ..smalltalk import classify, respond
from ..training import get_active_artifacts, get_active_version

router = APIRouter(prefix="/api/recommendations", tags=["recommendations"])

_WEIGHTS = {
    "relevance": settings.weight_relevance,
    "feasibility": settings.weight_feasibility,
    "faculty": settings.weight_faculty,
}
_KW = dict(
    gate_threshold=settings.gate_threshold,
    concentration_min=settings.topic_concentration_min,
    split_ratio=settings.domain_split_ratio,
    weights=_WEIGHTS,
    mmr_lambda=settings.mmr_lambda,
    top_k=settings.top_k,
)
# chat replies show fewer results than the full recommendations page
CHAT_TOP_K = 3


def _smalltalk_response(student: Student, intent: str) -> RecommendationResponse:
    """A greeting / identity / thanks / farewell / off-topic message - answered
    with a fixed reply, the recommendation engine never runs. Same response
    shape as a normal turn so the frontend can render it as a plain bubble."""
    return RecommendationResponse(
        student_id=student.id,
        model_version=None,
        mode="smalltalk",
        message=respond(intent, student.name),
        scoring_formula="",
        weights={},
        recommendations=[],
        refinement={"intent": intent},
    )


def _generate_response(db: Session, student: Student, text: str) -> RecommendationResponse:
    """Generate mode: new ideas from the offline generator - never corpus rows,
    never a Project ID."""
    domain = map_domain(text)
    ideas: list[dict] = []
    if domain is None:
        message = ("Which domain should the new ideas be in? I can generate ideas for: "
                   f"{', '.join(DOMAINS)}.")
    else:
        level = map_level(text)
        ideas = generate_ideas(get_active_artifacts(db), domain, level, count=3, interests=text)
        message = (f"Here are {len(ideas)} new {domain} project ideas at {level} level, "
                   f"each labelled \"{GENERATED_LABEL}\".")
    return RecommendationResponse(
        student_id=student.id,
        model_version=None,
        mode="generated",
        message=message,
        scoring_formula="",
        weights={},
        recommendations=[],
        refinement={"intent": "generate", "domain": domain},
        generated_ideas=ideas,
    )


def _chat_trim(result: RecResult) -> RecResult:
    """Top 3 only. Off-topic / no-signal results already carry no projects -
    there is no "closest available" fallback."""
    result.recommendations = result.recommendations[:CHAT_TOP_K]
    for i, r in enumerate(result.recommendations, start=1):
        r.rank = i
    return result


def _source_tag(ps: ProblemStatement) -> str:
    if ps.source:
        return ps.source
    return "department catalogue" if ps.source_batch == "initial" else ps.source_batch


def _profile(student: Student) -> StudentProfile:
    return StudentProfile(
        skills=json.loads(student.skills or "[]"),
        interests=json.loads(student.interests or "[]"),
        prior_projects=student.prior_projects or "",
        tech_comfort=student.tech_comfort or "moderate",
        preferred_outcome=student.preferred_outcome or "",
    )


def _respond(
    db: Session, student: Student, result: RecResult, version: int | None, refinement=None
) -> RecommendationResponse:
    """Persist one Recommendation row per shown item, then echo its id back so the
    feedback endpoint has a target."""
    from ..ml.pipeline import ModelArtifacts  # local import to keep module load light

    art: ModelArtifacts | None = get_active_artifacts(db)
    ps_id_by_project = {m.project_id: m.id for m in (art.docs_meta if art else [])}
    ps_by_id = {
        ps.id: ps
        for ps in db.scalars(
            select(ProblemStatement).where(
                ProblemStatement.id.in_([ps_id_by_project.get(r.project_id, 0)
                                         for r in result.recommendations])
            )
        )
    }

    items = []
    for rec in result.recommendations:
        row = Recommendation(
            student_id=student.id,
            problem_statement_id=ps_id_by_project.get(rec.project_id, 0),
            score=rec.composite_score,
            # legacy column name; holds the document-level gate score now
            cluster_confidence=result.gate_score,
            rank=rec.rank,
            model_version=version,
            details=json.dumps(rec.explanation),
        )
        db.add(row)
        db.flush()  # assign row.id without ending the transaction
        d = rec.as_dict()
        d["recommendation_id"] = row.id
        ps = ps_by_id.get(row.problem_statement_id)
        snippet = " ".join((rec.statement or "").split())
        d["short_description"] = snippet if len(snippet) <= 200 else snippet[:197].rstrip() + "…"
        d["source"] = _source_tag(ps) if ps else None
        d["domain"] = rec.domain or (ps.domain if ps else None)
        d["field"] = ps.field if ps else None
        d["difficulty"] = ps.difficulty if ps else None
        items.append(d)
    db.commit()

    return RecommendationResponse(
        student_id=student.id,
        model_version=version,
        mode=result.mode,
        message=result.message,
        routed_domains=result.routed_domains,
        routing_source=result.routing_source,
        domain_probabilities=result.domain_probabilities,
        gate_score=result.gate_score,
        gate_threshold=result.gate_threshold,
        topic_concentration=result.topic_concentration,
        suggested_domains=result.suggested_domains,
        scoring_formula=result.scoring_formula,
        weights=result.weights,
        recommendations=items,
        refinement=refinement,
    )


@router.post("", response_model=RecommendationResponse)
def create_recommendations(
    payload: RecommendationRequest, db: Session = Depends(get_db)
) -> RecommendationResponse:
    student = db.get(Student, payload.student_id)
    if student is None:
        raise HTTPException(404, f"student {payload.student_id} not found")

    art = get_active_artifacts(db)
    if art is None:
        raise HTTPException(503, "no active model - run POST /api/model/retrain first")
    version = get_active_version(db).version

    exclude = set(payload.filters.get("exclude_project_ids", []))
    result = recommend(art, _profile(student), exclude_project_ids=exclude, **_KW)
    return _respond(db, student, result, version)


@router.post("/refine", response_model=RecommendationResponse)
def refine_recommendations(
    payload: RefineRequest, db: Session = Depends(get_db)
) -> RecommendationResponse:
    student = db.get(Student, payload.student_id)
    if student is None:
        raise HTTPException(404, f"student {payload.student_id} not found")

    # greeting / identity / thanks / farewell / off-topic -> fixed reply,
    # the recommendation engine never runs and can't invent a project.
    route = classify(payload.constraint)
    if route.destination == "smalltalk":
        return _smalltalk_response(student, route.intent)
    if route.destination == "generate":
        return _generate_response(db, student, payload.constraint)

    art = get_active_artifacts(db)
    if art is None:
        raise HTTPException(503, "no active model - run POST /api/model/retrain first")
    version = get_active_version(db).version

    result, parse = refine(art, _profile(student), payload.constraint, **_KW)
    if payload.exclude_project_ids:
        ex = set(payload.exclude_project_ids)
        result.recommendations = [r for r in result.recommendations if r.project_id not in ex]
        for i, r in enumerate(result.recommendations, start=1):
            r.rank = i
    return _respond(db, student, _chat_trim(result), version, refinement=parse.as_dict())
