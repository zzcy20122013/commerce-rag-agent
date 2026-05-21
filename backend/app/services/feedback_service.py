import uuid

from sqlalchemy.orm import Session

from app.models.tables import Feedback


def create_feedback(db: Session, *, message_id: str, rating: int, reason: str = "") -> Feedback:
    feedback = Feedback(
        id=f"fb_{uuid.uuid4().hex[:12]}",
        message_id=message_id,
        rating=rating,
        reason=reason,
    )
    db.add(feedback)
    db.commit()
    db.refresh(feedback)
    return feedback
