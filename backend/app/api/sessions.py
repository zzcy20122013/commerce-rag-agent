from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.models.db import get_db, init_db
from app.services.session_service import ensure_session, list_sessions


router = APIRouter(prefix="/api/sessions", tags=["sessions"])


class CreateSessionRequest(BaseModel):
    title: str = "导购会话"


@router.get("")
def get_sessions(db: Session = Depends(get_db)) -> list[dict]:
    init_db()
    return [
        {
            "id": session.id,
            "title": session.title,
            "updatedAt": session.updated_at.isoformat(),
        }
        for session in list_sessions(db)
    ]


@router.post("")
def create_session(payload: CreateSessionRequest, db: Session = Depends(get_db)) -> dict:
    init_db()
    session = ensure_session(db)
    session.title = payload.title
    db.commit()
    db.refresh(session)
    return {
        "id": session.id,
        "title": session.title,
        "updatedAt": session.updated_at.isoformat(),
    }
