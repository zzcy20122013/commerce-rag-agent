import uuid
import json

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models.tables import ChatSession, Feedback, Message, RecommendationLog, RetrievalLog, utc_now


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


def update_session_title(db: Session, *, session_id: str, title: str) -> ChatSession | None:
    session = db.get(ChatSession, session_id)
    if not session:
        return None

    session.title = title
    session.updated_at = utc_now()
    db.commit()
    db.refresh(session)
    return session


def update_session_title_from_first_message(db: Session, *, session_id: str, message: str) -> ChatSession | None:
    session = db.get(ChatSession, session_id)
    if not session:
        return None
    if (session.title or "").strip() not in {"", "导购会话", "新导购会话"}:
        return session

    title = auto_title_from_first_user_message(message)
    session.title = title
    session.updated_at = utc_now()
    db.commit()
    db.refresh(session)
    return session


def auto_title_from_first_user_message(message: str) -> str:
    text = (message or "").strip()
    if not text:
        return "导购会话"

    topic = _first_matching_topic(text)
    modifier = _first_matching_modifier(text)
    if topic and modifier and modifier not in topic:
        return _fit_session_title(f"{modifier}{topic}选购")
    if topic:
        return _fit_session_title(f"{topic}选购")

    cleaned = _clean_title_text(text)
    return _fit_session_title(cleaned or "导购会话")


def _first_matching_topic(text: str) -> str:
    topics = [
        "蓝牙耳机",
        "降噪耳机",
        "速干T恤",
        "洗面奶",
        "防晒霜",
        "定妆粉",
        "粉饼",
        "散粉",
        "精华",
        "面霜",
        "平板",
        "电脑",
        "手机",
        "耳机",
        "通勤鞋",
        "跑鞋",
        "鞋",
        "背包",
        "饮料",
        "咖啡",
        "麦片",
        "方便面",
    ]
    for topic in topics:
        if topic in text:
            return topic
    return ""


def _first_matching_modifier(text: str) -> str:
    modifiers = [
        "敏感肌",
        "油皮",
        "学生",
        "通勤",
        "跑步",
        "户外",
        "办公室",
        "早餐",
        "无糖",
        "低糖",
        "轻便",
    ]
    for modifier in modifiers:
        if modifier in text:
            return modifier
    return ""


def _clean_title_text(text: str) -> str:
    cleaned = text
    for token in ["我想买", "帮我找", "帮我推荐", "推荐", "有没有", "有哪些", "一款", "一个", "适合"]:
        cleaned = cleaned.replace(token, "")
    for char in ["，", "。", "？", "?", "！", "!", ","]:
        cleaned = cleaned.replace(char, " ")
    return " ".join(cleaned.split())


def _fit_session_title(title: str, max_length: int = 12) -> str:
    compact = "".join(title.split())
    return compact[:max_length] if len(compact) > max_length else compact


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
