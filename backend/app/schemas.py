"""Pydantic request/response models."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator


# --------------------------------------------------------------------------- #
# students
# --------------------------------------------------------------------------- #
class StudentIn(BaseModel):
    id: int | None = None
    name: str = Field(min_length=1, max_length=160)
    skills: list[str] = Field(default_factory=list)
    interests: list[str] = Field(default_factory=list)
    tech_comfort: str = "moderate"
    prior_projects: str = ""
    preferred_outcome: str = ""

    @field_validator("skills", "interests", mode="before")
    @classmethod
    def _split(cls, v: Any) -> list[str]:
        if isinstance(v, str):
            return [s.strip() for s in v.replace("\n", ",").split(",") if s.strip()]
        if isinstance(v, list):
            return [str(s).strip() for s in v if str(s).strip()]
        return []


class StudentOut(BaseModel):
    id: int
    name: str
    skills: list[str]
    interests: list[str]
    tech_comfort: str
    prior_projects: str
    preferred_outcome: str
    created_at: datetime

    @classmethod
    def from_model(cls, m: Any) -> "StudentOut":
        return cls(
            id=m.id,
            name=m.name,
            skills=json.loads(m.skills or "[]"),
            interests=json.loads(m.interests or "[]"),
            tech_comfort=m.tech_comfort,
            prior_projects=m.prior_projects or "",
            preferred_outcome=m.preferred_outcome or "",
            created_at=m.created_at,
        )


# --------------------------------------------------------------------------- #
# recommendations
# --------------------------------------------------------------------------- #
class RecommendationRequest(BaseModel):
    student_id: int
    filters: dict[str, Any] = Field(default_factory=dict)


class RefineRequest(BaseModel):
    student_id: int
    constraint: str = Field(min_length=1, max_length=400)
    exclude_project_ids: list[str] = Field(default_factory=list)


class RecommendationResponse(BaseModel):
    student_id: int
    model_version: int | None
    mode: str
    message: str
    routed_cluster: int | None
    routed_clusters: list[int] = Field(default_factory=list)
    cluster_confidence: float
    cluster_distribution: list[dict[str, Any]]
    scoring_formula: str
    weights: dict[str, float]
    faculty_matching_active: bool = False
    faculty_matching_note: str = (
        "Faculty matching: not yet active - no preference data collected."
    )
    recommendations: list[dict[str, Any]]
    refinement: dict[str, Any] | None = None


# --------------------------------------------------------------------------- #
# corpus
# --------------------------------------------------------------------------- #
class ProblemStatementOut(BaseModel):
    id: int
    project_id: str
    title: str | None
    statement: str | None
    cluster_id: int | None
    cluster_label: str | None = None
    is_flagged: bool
    flag_reason: str | None
    source_batch: str
    original_project_id: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CorpusPage(BaseModel):
    items: list[ProblemStatementOut]
    total: int
    page: int
    page_size: int
    pages: int


class ProblemStatementPatch(BaseModel):
    project_id: str | None = None
    title: str | None = None
    statement: str | None = None
    clear_flag: bool = True


class UploadReport(BaseModel):
    source_batch: str
    report: dict[str, Any]
    inserted: int
    retrain_recommended: bool = True


# --------------------------------------------------------------------------- #
# model
# --------------------------------------------------------------------------- #
class ModelVersionOut(BaseModel):
    version: int
    corpus_size: int
    cluster_count: int
    silhouette: float
    trained_at: datetime
    is_active: bool
    notes: str
    params: dict[str, Any]

    @classmethod
    def from_model(cls, m: Any) -> "ModelVersionOut":
        return cls(
            version=m.version,
            corpus_size=m.corpus_size,
            cluster_count=m.cluster_count,
            silhouette=m.silhouette,
            trained_at=m.trained_at,
            is_active=m.is_active,
            notes=m.notes or "",
            params=json.loads(m.params or "{}"),
        )


class ModelStatus(BaseModel):
    active_version: int | None
    corpus_size: int
    active_corpus_size: int
    flagged_count: int
    cluster_count: int | None
    last_trained_at: datetime | None
    silhouette: float | None
    silhouette_by_k: dict[str, float] = Field(default_factory=dict)
    clusters: list[dict[str, Any]] = Field(default_factory=list)
    faculty_matching_active: bool = False
    faculty_matching_note: str = (
        "Faculty matching: not yet active - no preference data collected."
    )
    versions: list[ModelVersionOut] = Field(default_factory=list)


class RetrainRequest(BaseModel):
    notes: str = ""


class ActivateRequest(BaseModel):
    version: int


# --------------------------------------------------------------------------- #
# feedback + faculty
# --------------------------------------------------------------------------- #
class FeedbackIn(BaseModel):
    recommendation_id: int
    verdict: str

    @field_validator("verdict")
    @classmethod
    def _check(cls, v: str) -> str:
        v = v.lower().strip()
        if v not in {"accept", "reject"}:
            raise ValueError("verdict must be 'accept' or 'reject'")
        return v


class FeedbackOut(BaseModel):
    id: int
    recommendation_id: int
    verdict: str
    created_at: datetime

    model_config = {"from_attributes": True}


class FacultyPreferenceIn(BaseModel):
    faculty_name: str = Field(min_length=1, max_length=160)
    domain: str = Field(min_length=1, max_length=160)
    notes: str = ""


class FacultyPreferenceOut(BaseModel):
    id: int
    faculty_name: str
    domain: str
    notes: str
    created_at: datetime

    model_config = {"from_attributes": True}


class FacultyPreferenceList(BaseModel):
    items: list[FacultyPreferenceOut]
    active_in_scoring: bool = False
    note: str = (
        "The FACULTY DETAILS sheet in the source workbook is a review-assignment "
        "tracker, not preference data. Faculty matching stays weighted at 0 in the "
        "scoring formula until real preferences are entered here."
    )
