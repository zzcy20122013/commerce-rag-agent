import json

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.sessions import get_db, router as sessions_router
from app.models.db import Base
from app.models.tables import ChatSession, Feedback, Message, RecommendationLog, RetrievalLog
from app.services.log_service import log_recommendation, log_retrieval
from app.services.session_service import (
    add_message,
    auto_title_from_first_user_message,
    delete_session,
    ensure_session,
    list_session_messages,
    update_session_title,
    update_session_title_from_first_message,
)


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


def test_update_session_title_persists_to_database(monkeypatch) -> None:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSession = sessionmaker(bind=engine)
    Base.metadata.create_all(bind=engine)

    db = TestingSession()
    session = ensure_session(db, session_id="sess_rename")
    db.close()

    def override_get_db():
        request_db = TestingSession()
        try:
            yield request_db
        finally:
            request_db.close()

    monkeypatch.setattr("app.api.sessions.init_db", lambda: None)
    app = FastAPI()
    app.include_router(sessions_router)
    app.dependency_overrides[get_db] = override_get_db

    response = TestClient(app).put(f"/api/sessions/{session.id}", json={"title": "通勤耳机选购"})

    assert response.status_code == 200
    assert response.json()["title"] == "通勤耳机选购"

    verify_db = TestingSession()
    try:
        updated = verify_db.get(ChatSession, session.id)
        assert updated is not None
        assert updated.title == "通勤耳机选购"
    finally:
        verify_db.close()


def test_update_session_title_rejects_blank_title(monkeypatch) -> None:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSession = sessionmaker(bind=engine)
    Base.metadata.create_all(bind=engine)

    db = TestingSession()
    session = ensure_session(db, session_id="sess_blank_title")
    db.close()

    def override_get_db():
        request_db = TestingSession()
        try:
            yield request_db
        finally:
            request_db.close()

    monkeypatch.setattr("app.api.sessions.init_db", lambda: None)
    app = FastAPI()
    app.include_router(sessions_router)
    app.dependency_overrides[get_db] = override_get_db

    response = TestClient(app).put(f"/api/sessions/{session.id}", json={"title": "   "})

    assert response.status_code == 400

    verify_db = TestingSession()
    try:
        unchanged = verify_db.get(ChatSession, session.id)
        assert unchanged is not None
        assert unchanged.title == "导购会话"
    finally:
        verify_db.close()


def test_auto_title_from_first_user_message_extracts_shopping_topic() -> None:
    assert auto_title_from_first_user_message("我想买 3500 以内适合学生记笔记和网课的平板") == "学生平板选购"
    assert auto_title_from_first_user_message("推荐 300 以内适合通勤的鞋") == "通勤鞋选购"
    assert auto_title_from_first_user_message("50 元以内适合敏感肌修护维稳的精华") == "敏感肌精华选购"


def test_update_session_title_from_first_message_only_updates_default_title() -> None:
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    TestingSession = sessionmaker(bind=engine)
    Base.metadata.create_all(bind=engine)

    db = TestingSession()
    try:
        session = ensure_session(db, session_id="sess_auto_title")
        updated = update_session_title_from_first_message(
            db,
            session_id=session.id,
            message="我想买 3500 以内适合学生记笔记和网课的平板",
        )

        assert updated is not None
        assert updated.title == "学生平板选购"

        update_session_title(db, session_id=session.id, title="我自己命名")
        unchanged = update_session_title_from_first_message(
            db,
            session_id=session.id,
            message="推荐 300 以内适合通勤的鞋",
        )

        assert unchanged is not None
        assert unchanged.title == "我自己命名"
    finally:
        db.close()
