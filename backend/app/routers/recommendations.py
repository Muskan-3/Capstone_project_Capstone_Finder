from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..config import settings
from ..db import get_db
from ..ml.recommender import RecResult, StudentProfile, recommend, refine
from ..models import Recommendation, Student
from ..schemas import RecommendationRequest, RecommendationResponse, RefineRequest
from ..training import get_active_artifacts, get_active_version

router = APIRouter(prefix="/api/recommendations", tags=["recommendations"])

_WEIGHTS = {
    "relevance": settings.weight_relevance,
    "feasibility": settings.weight_feasibility,
    "faculty": settings.weight_faculty,
}
_KW = dict(
    route_threshold=settings.route_confidence_threshold,
    serendipity=settings.serendipity_cross_cluster,
    weights=_WEIGHTS,
    mmr_lambda=settings.mmr_lambda,
    top_k=settings.top_k,
    band_strong=settings.band_strong,
    band_moderate=settings.band_moderate,
)


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

    items = []
    for rec in result.recommendations:
        row = Recommendation(
            student_id=student.id,
            problem_statement_id=ps_id_by_project.get(rec.project_id, 0),
            score=rec.composite_score,
            cluster_confidence=result.cluster_confidence,
            rank=rec.rank,
            model_version=version,
            details=json.dumps(rec.explanation),
        )
        db.add(row)
        db.flush()  # assign row.id without ending the transaction
        d = rec.as_dict()
        d["recommendation_id"] = row.id
        items.append(d)
    db.commit()

    return RecommendationResponse(
        student_id=student.id,
        model_version=version,
        mode=result.mode,
        message=result.message,
        routed_cluster=result.routed_cluster,
        routed_clusters=result.routed_clusters,
        cluster_confidence=result.cluster_confidence,
        cluster_distribution=result.cluster_distribution,
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
    return _respond(db, student, result, version, refinement=parse.as_dict())
