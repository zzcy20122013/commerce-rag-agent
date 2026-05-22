import json

from sqlalchemy import select
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.db import Base
from app.models.tables import ChatSession, Feedback, Message, RecommendationLog, RetrievalLog
from app.services.log_service import log_recommendation, log_retrieval
from app.services.session_service import add_message, delete_session, ensure_session, list_session_messages


def test_list_session_messages_includes_recommendation_cards() -> None:
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    TestingSession = sessionmaker(bind=engine)
    Base.metadata.create_all(bind=engine)

    db = TestingSession()
    try:
        session = ensure_session(db, session_id="sess_history")
        user_message = add_message(db, session_id=session.id, role="user", content="推荐通勤鞋")
        assistant_message = add_message(db, session_id=session.id, role="assistant", content="更建议你看第一双。")
        cards = [
            {
                "product_id": "p_shoes_001",
                "title": "轻便通勤鞋",
                "subtitle": "适合日常通勤",
                "price": 199,
                "image_url": "/static/product_images/p_shoes_001.png",
                "rating": 4.6,
                "sales": 1200,
                "reasons": ["通勤", "轻便"],
            }
        ]
        log_recommendation(db, session_id=session.id, message_id=assistant_message.id, products=cards)

        history = list_session_messages(db, session_id=session.id)

        assert [message["id"] for message in history] == [user_message.id, assistant_message.id]
        assert history[0]["role"] == "user"
        assert history[0]["productCards"] == []
        assert history[1]["role"] == "assistant"
        assert json.dumps(history[1]["productCards"], ensure_ascii=False) == json.dumps(cards, ensure_ascii=False)
    finally:
        db.close()


def test_delete_session_removes_history_logs_and_feedback() -> None:
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    TestingSession = sessionmaker(bind=engine)
    Base.metadata.create_all(bind=engine)

    db = TestingSession()
    try:
        session = ensure_session(db, session_id="sess_delete")
        user_message = add_message(db, session_id=session.id, role="user", content="推荐通勤鞋")
        assistant_message = add_message(db, session_id=session.id, role="assistant", content="更建议你看第一双。")
        user_message_id = user_message.id
        log_recommendation(db, session_id=session.id, message_id=assistant_message.id, products=[])
        log_retrieval(
            db,
            session_id=session.id,
            query="推荐通勤鞋",
            intent="shopping_guide",
            filters={"category": "鞋"},
            candidates=[],
        )
        db.add(Feedback(id="fb_delete", message_id=assistant_message.id, rating=1, reason="ok"))
        db.commit()

        deleted = delete_session(db, session_id=session.id)

        assert deleted is True
        assert db.get(ChatSession, session.id) is None
        assert db.scalars(select(Message).where(Message.session_id == session.id)).all() == []
        assert db.scalars(select(RecommendationLog).where(RecommendationLog.session_id == session.id)).all() == []
        assert db.scalars(select(RetrievalLog).where(RetrievalLog.session_id == session.id)).all() == []
        assert db.get(Feedback, "fb_delete") is None
        assert db.get(Message, user_message_id) is None
    finally:
        db.close()
