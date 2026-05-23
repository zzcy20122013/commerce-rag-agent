from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.models.db import get_db, init_db
from app.models.tables import ChatSession
from app.services.session_service import delete_session, ensure_session, list_session_messages, list_sessions, update_session_title


router = APIRouter(prefix="/api/sessions", tags=["sessions"])


class CreateSessionRequest(BaseModel):
    title: str = "导购会话"


class UpdateSessionRequest(BaseModel):
    title: str


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


@router.put("/{session_id}")
def update_session(session_id: str, payload: UpdateSessionRequest, db: Session = Depends(get_db)) -> dict:
    init_db()
    title = payload.title.strip()
    if not title:
        raise HTTPException(status_code=400, detail="Session title cannot be empty")

    session = update_session_title(db, session_id=session_id, title=title)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    return {
        "id": session.id,
        "title": session.title,
        "updatedAt": session.updated_at.isoformat(),
    }


@router.get("/{session_id}/messages")
def get_session_messages(session_id: str, db: Session = Depends(get_db)) -> list[dict]:
    init_db()
    if not db.get(ChatSession, session_id):
        raise HTTPException(status_code=404, detail="Session not found")
    return list_session_messages(db, session_id=session_id)


@router.delete("/{session_id}")
def remove_session(session_id: str, db: Session = Depends(get_db)) -> dict:
    init_db()
    if not delete_session(db, session_id=session_id):
        raise HTTPException(status_code=404, detail="Session not found")
    return {"ok": True, "session_id": session_id}
