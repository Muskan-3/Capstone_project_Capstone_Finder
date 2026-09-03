from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import ModelVersion, ProblemStatement
from ..schemas import ActivateRequest, ModelStatus, ModelVersionOut, RetrainRequest
from ..training import activate_version, get_active_artifacts, get_active_version, retrain

router = APIRouter(prefix="/api/model", tags=["model"])


@router.get("/status", response_model=ModelStatus)
def model_status(db: Session = Depends(get_db)) -> ModelStatus:
    total = db.scalar(select(func.count()).select_from(ProblemStatement)) or 0
    flagged = db.scalar(
        select(func.count()).select_from(ProblemStatement).where(
            ProblemStatement.is_flagged.is_(True)
        )
    ) or 0
    active = get_active_version(db)
    art = get_active_artifacts(db)
    versions = db.scalars(select(ModelVersion).order_by(ModelVersion.version.desc())).all()

    clusters: list[dict] = []
    silhouette_by_k: dict[str, float] = {}
    if art:
        summary = art.status_summary()
        clusters = summary["clusters"]
        silhouette_by_k = {str(k): v for k, v in summary["silhouette_by_k"].items()}

    return ModelStatus(
        active_version=active.version if active else None,
        corpus_size=total,
        active_corpus_size=total - flagged,
        flagged_count=flagged,
        cluster_count=active.cluster_count if active else None,
        last_trained_at=active.trained_at if active else None,
        silhouette=active.silhouette if active else None,
        silhouette_by_k=silhouette_by_k,
        clusters=clusters,
        versions=[ModelVersionOut.from_model(v) for v in versions],
    )


@router.post("/retrain", response_model=ModelVersionOut)
def trigger_retrain(
    payload: RetrainRequest | None = None, db: Session = Depends(get_db)
) -> ModelVersionOut:
    try:
        mv = retrain(db, notes=(payload.notes if payload else ""))
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    return ModelVersionOut.from_model(mv)


@router.post("/activate", response_model=ModelVersionOut)
def set_active(payload: ActivateRequest, db: Session = Depends(get_db)) -> ModelVersionOut:
    try:
        mv = activate_version(db, payload.version)
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc
    return ModelVersionOut.from_model(mv)
