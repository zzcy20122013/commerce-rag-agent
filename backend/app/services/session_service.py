import uuid
import json

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models.tables import ChatSession, Feedback, Message, RecommendationLog, RetrievalLog


def ensure_session(db: Session, *, session_id: str | None = None, user_id: str = "debug-user") -> ChatSession:
    if session_id:
        existing = db.get(ChatSession, session_id)
        if existing:
            return existing
    session = ChatSession(id=session_id or f"sess_{uuid.uuid4().hex[:12]}", user_id=user_id, title="导购会话")
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def list_sessions(db: Session, *, user_id: str = "debug-user") -> list[ChatSession]:
    statement = (
        select(ChatSession)
        .where(ChatSession.user_id == user_id)
        .order_by(ChatSession.updated_at.desc())
    )
    return list(db.scalars(statement).all())


def add_message(db: Session, *, session_id: str, role: str, content: str, metadata_json: str = "{}") -> Message:
    message = Message(
        id=f"msg_{uuid.uuid4().hex[:12]}",
        session_id=session_id,
        role=role,
        content=content,
        metadata_json=metadata_json,
    )
    db.add(message)
    db.commit()
    db.refresh(message)
    return message


def get_latest_memory(db: Session, *, session_id: str) -> dict:
    statement = (
        select(Message)
        .where(Message.session_id == session_id)
        .where(Message.role == "assistant")
        .order_by(Message.created_at.desc())
    )
    for message in db.scalars(statement).all():
        try:
            metadata = json.loads(message.metadata_json or "{}")
        except json.JSONDecodeError:
            continue
        memory = metadata.get("memory")
        if isinstance(memory, dict):
            return memory
    return {}


def list_session_messages(db: Session, *, session_id: str) -> list[dict]:
    messages = list(
        db.scalars(
            select(Message)
            .where(Message.session_id == session_id)
            .order_by(Message.created_at.asc())
        ).all()
    )
    if not messages:
        return []

    recommendation_logs = list(
        db.scalars(
            select(RecommendationLog)
            .where(RecommendationLog.session_id == session_id)
        ).all()
    )
    cards_by_message_id: dict[str, list] = {}
    for log in recommendation_logs:
        try:
            cards = json.loads(log.products_json or "[]")
        except json.JSONDecodeError:
            cards = []
        if isinstance(cards, list):
            cards_by_message_id[log.message_id] = cards

    return [
        {
            "id": message.id,
            "role": message.role,
            "content": message.content,
            "createdAt": message.created_at.isoformat(),
            "productCards": cards_by_message_id.get(message.id, []),
        }
        for message in messages
    ]


def delete_session(db: Session, *, session_id: str) -> bool:
    session = db.get(ChatSession, session_id)
    if not session:
        return False

    message_ids = list(
        db.scalars(
            select(Message.id)
            .where(Message.session_id == session_id)
        ).all()
    )
    if message_ids:
        db.execute(delete(Feedback).where(Feedback.message_id.in_(message_ids)))

    db.execute(delete(RecommendationLog).where(RecommendationLog.session_id == session_id))
    db.execute(delete(RetrievalLog).where(RetrievalLog.session_id == session_id))
    db.execute(delete(Message).where(Message.session_id == session_id))
    db.delete(session)
    db.commit()
    return True
