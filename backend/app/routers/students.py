from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Student
from ..schemas import StudentIn, StudentOut

router = APIRouter(prefix="/api/students", tags=["students"])


@router.post("", response_model=StudentOut)
def upsert_student(payload: StudentIn, db: Session = Depends(get_db)) -> StudentOut:
    if payload.id is not None:
        student = db.get(Student, payload.id)
        if student is None:
            raise HTTPException(404, f"student {payload.id} not found")
    else:
        student = Student()
        db.add(student)

    student.name = payload.name
    student.skills = json.dumps(payload.skills)
    student.interests = json.dumps(payload.interests)
    student.tech_comfort = payload.tech_comfort
    student.prior_projects = payload.prior_projects
    student.preferred_outcome = payload.preferred_outcome
    db.commit()
    db.refresh(student)
    return StudentOut.from_model(student)


@router.get("/{student_id}", response_model=StudentOut)
def get_student(student_id: int, db: Session = Depends(get_db)) -> StudentOut:
    student = db.get(Student, student_id)
    if student is None:
        raise HTTPException(404, f"student {student_id} not found")
    return StudentOut.from_model(student)
