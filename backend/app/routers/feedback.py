from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Feedback, Recommendation
from ..schemas import FeedbackIn, FeedbackOut

router = APIRouter(prefix="/api/feedback", tags=["feedback"])


@router.post("", response_model=FeedbackOut)
def submit_feedback(payload: FeedbackIn, db: Session = Depends(get_db)) -> FeedbackOut:
    rec = db.get(Recommendation, payload.recommendation_id)
    if rec is None:
        raise HTTPException(404, f"recommendation {payload.recommendation_id} not found")
    fb = Feedback(recommendation_id=payload.recommendation_id, verdict=payload.verdict)
    db.add(fb)
    db.commit()
    db.refresh(fb)
    return FeedbackOut.model_validate(fb)
