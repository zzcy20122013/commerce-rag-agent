from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.models.db import get_db, init_db
from app.models.tables import Message
from app.services.feedback_service import create_feedback


router = APIRouter(prefix="/api/feedback", tags=["feedback"])


class FeedbackRequest(BaseModel):
    message_id: str
    rating: int
    reason: str = ""


@router.post("")
def submit_feedback(payload: FeedbackRequest, db: Session = Depends(get_db)) -> dict:
    init_db()
    if payload.rating not in {-1, 1}:
        raise HTTPException(status_code=400, detail="rating must be 1 or -1")
    if not db.get(Message, payload.message_id):
        raise HTTPException(status_code=404, detail="Message not found")
    feedback = create_feedback(
        db,
        message_id=payload.message_id,
        rating=payload.rating,
        reason=payload.reason,
    )
    return {"id": feedback.id, "message_id": feedback.message_id, "rating": feedback.rating}
