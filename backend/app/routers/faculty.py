from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import FacultyPreference
from ..schemas import FacultyPreferenceIn, FacultyPreferenceList, FacultyPreferenceOut

router = APIRouter(prefix="/api/faculty-preferences", tags=["faculty"])


@router.get("", response_model=FacultyPreferenceList)
def list_preferences(db: Session = Depends(get_db)) -> FacultyPreferenceList:
    rows = db.scalars(select(FacultyPreference).order_by(FacultyPreference.id)).all()
    return FacultyPreferenceList(
        items=[FacultyPreferenceOut.model_validate(r) for r in rows],
        active_in_scoring=False,  # stays False until this list is populated AND weight > 0
    )


@router.post("", response_model=FacultyPreferenceOut)
def add_preference(
    payload: FacultyPreferenceIn, db: Session = Depends(get_db)
) -> FacultyPreferenceOut:
    row = FacultyPreference(
        faculty_name=payload.faculty_name.strip(),
        domain=payload.domain.strip(),
        notes=payload.notes.strip(),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return FacultyPreferenceOut.model_validate(row)
