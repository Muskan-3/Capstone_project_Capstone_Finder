"""Database schema (Section 8 of the build brief, with a few pragmatic additions)."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


class ProblemStatement(Base):
    __tablename__ = "problem_statements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[str] = mapped_column(String(80), index=True)
    title: Mapped[str | None] = mapped_column(Text, nullable=True)
    statement: Mapped[str | None] = mapped_column(Text, nullable=True)
    cluster_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    is_flagged: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    flag_reason: Mapped[str | None] = mapped_column(String(160), nullable=True)
    source_batch: Mapped[str] = mapped_column(String(80), default="initial", index=True)
    # kept for audit when ingestion rewrites a duplicated ProjectID
    original_project_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)

    recommendations: Mapped[list["Recommendation"]] = relationship(back_populates="problem_statement")


class Student(Base):
    __tablename__ = "students"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(160))
    skills: Mapped[str] = mapped_column(Text, default="")        # JSON array of strings
    interests: Mapped[str] = mapped_column(Text, default="")     # JSON array of strings
    tech_comfort: Mapped[str] = mapped_column(String(40), default="moderate")
    prior_projects: Mapped[str] = mapped_column(Text, default="")
    preferred_outcome: Mapped[str] = mapped_column(String(60), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)


class Recommendation(Base):
    __tablename__ = "recommendations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"), index=True)
    problem_statement_id: Mapped[int] = mapped_column(ForeignKey("problem_statements.id"))
    score: Mapped[float] = mapped_column(Float)
    cluster_confidence: Mapped[float] = mapped_column(Float)
    rank: Mapped[int] = mapped_column(Integer, default=0)
    model_version: Mapped[int | None] = mapped_column(Integer, nullable=True)
    details: Mapped[str] = mapped_column(Text, default="{}")  # JSON: cosine, term drivers, formula
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    problem_statement: Mapped[ProblemStatement] = relationship(back_populates="recommendations")
    feedback: Mapped[list["Feedback"]] = relationship(back_populates="recommendation")


class Feedback(Base):
    __tablename__ = "feedback"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    recommendation_id: Mapped[int] = mapped_column(ForeignKey("recommendations.id"), index=True)
    verdict: Mapped[str] = mapped_column(String(20))  # "accept" | "reject"
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    recommendation: Mapped[Recommendation] = relationship(back_populates="feedback")


class FacultyPreference(Base):
    __tablename__ = "faculty_preferences"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    faculty_name: Mapped[str] = mapped_column(String(160))
    domain: Mapped[str] = mapped_column(String(160))
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class ModelVersion(Base):
    __tablename__ = "model_versions"
    __table_args__ = (UniqueConstraint("version", name="uq_model_version"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    version: Mapped[int] = mapped_column(Integer, index=True)
    corpus_size: Mapped[int] = mapped_column(Integer)
    cluster_count: Mapped[int] = mapped_column(Integer)
    silhouette: Mapped[float] = mapped_column(Float, default=0.0)
    params: Mapped[str] = mapped_column(Text, default="{}")   # JSON snapshot of pipeline params
    notes: Mapped[str] = mapped_column(Text, default="")
    trained_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
