"""Glue between the database and the ML pipeline: (re)train + activate a version."""

from __future__ import annotations

import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from .config import settings
from .ml import store
from .ml.pipeline import DocMeta, ModelArtifacts, train
from .models import ModelVersion, ProblemStatement


def _active_docs(db: Session) -> list[DocMeta]:
    rows = db.scalars(
        select(ProblemStatement)
        .where(ProblemStatement.is_flagged.is_(False))
        .order_by(ProblemStatement.id)
    ).all()
    docs: list[DocMeta] = []
    for r in rows:
        if not r.title and not r.statement:
            continue
        docs.append(
            DocMeta(
                id=r.id,
                project_id=r.project_id,
                title=r.title or "",
                statement=r.statement or "",
                source_batch=r.source_batch,
            )
        )
    return docs


def retrain(db: Session, *, notes: str = "") -> ModelVersion:
    """Run the full Section 5 pipeline over the entire active corpus and activate it."""
    docs = _active_docs(db)
    version = store.next_version()
    artifacts: ModelArtifacts = train(
        docs,
        version=version,
        max_features=settings.tfidf_max_features,
        min_df=settings.tfidf_min_df,
        k_min=settings.kmeans_k_min,
        k_max=settings.kmeans_k_max,
        random_state=settings.random_state,
    )
    store.save(artifacts)

    # write cluster assignments back onto the corpus rows
    cluster_by_id = dict(zip(artifacts.doc_ids, (int(c) for c in artifacts.doc_clusters)))
    for r in db.scalars(select(ProblemStatement)).all():
        r.cluster_id = cluster_by_id.get(r.id)

    for mv in db.scalars(select(ModelVersion).where(ModelVersion.is_active.is_(True))).all():
        mv.is_active = False

    mv = ModelVersion(
        version=version,
        corpus_size=artifacts.corpus_size,
        cluster_count=artifacts.k,
        silhouette=artifacts.silhouette,
        params=json.dumps(artifacts.params),
        notes=notes,
        is_active=True,
    )
    db.add(mv)
    db.commit()
    db.refresh(mv)
    store.evict()  # force a reload keyed on the new active version
    return mv


def get_active_version(db: Session) -> ModelVersion | None:
    return db.scalars(
        select(ModelVersion).where(ModelVersion.is_active.is_(True))
    ).first()


def get_active_artifacts(db: Session) -> ModelArtifacts | None:
    mv = get_active_version(db)
    if mv is None:
        return None
    if not store.has(mv.version):
        return None
    return store.load(mv.version)


def activate_version(db: Session, version: int) -> ModelVersion:
    target = db.scalars(
        select(ModelVersion).where(ModelVersion.version == version)
    ).first()
    if target is None:
        raise ValueError(f"model version {version} does not exist")
    if not store.has(version):
        raise ValueError(f"model version {version} has no saved artifact on disk")
    for mv in db.scalars(select(ModelVersion).where(ModelVersion.is_active.is_(True))).all():
        mv.is_active = False
    target.is_active = True

    art = store.load(version)
    cluster_by_id = dict(zip(art.doc_ids, (int(c) for c in art.doc_clusters)))
    for r in db.scalars(select(ProblemStatement)).all():
        r.cluster_id = cluster_by_id.get(r.id)

    db.commit()
    db.refresh(target)
    store.evict()
    return target
