from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.agents.shopping_guide import hybrid_retrieve_and_rerank
from app.models.db import Base
from app.models.tables import Product
from app.services.keyword_retrieval_service import KeywordRetrievalService


def test_keyword_retrieval_prioritizes_exact_commerce_terms() -> None:
    db = _seed_products()
    try:
        hits = KeywordRetrievalService().search(
            db,
            "通勤降噪耳机",
            memory={"category": "数码电子", "subcategory": "耳机", "use_cases": ["通勤"]},
        )

        assert hits
        assert hits[0]["product_id"] == "p_audio_001"
        assert hits[0]["matched_terms"]
    finally:
        db.close()


def test_hybrid_retrieval_falls_back_to_keyword_rerank_when_vector_fails(monkeypatch) -> None:
    db = _seed_products()
    products = list(db.query(Product).all())

    class BrokenTextIndex:
        def ensure_products_indexed(self, db):
            raise RuntimeError("vector unavailable")

    monkeypatch.setattr("app.agents.shopping_guide.TextIndex", BrokenTextIndex)

    ranked, trace = hybrid_retrieve_and_rerank(
        db,
        products,
        {"category": "数码电子", "subcategory": "耳机", "use_cases": ["通勤"]},
        "通勤降噪耳机",
    )

    assert ranked[0].id == "p_audio_001"
    assert trace["retrieval_mode"] == "sqlite_filter_keyword_rerank"
    assert "p_audio_001" in trace["keyword_hits"]
    assert trace["scoring"] == "bm25_rules"


def test_hybrid_retrieval_marks_low_confidence_when_no_keyword_or_vector_signal(monkeypatch) -> None:
    db = _seed_products()
    products = list(db.query(Product).all())

    class BrokenTextIndex:
        def ensure_products_indexed(self, db):
            raise RuntimeError("vector unavailable")

    monkeypatch.setattr("app.agents.shopping_guide.TextIndex", BrokenTextIndex)

    _, trace = hybrid_retrieve_and_rerank(db, products, {}, "火星露营飞船")

    assert trace["low_confidence"] is True
    assert trace["confidence"] == 0.0


def _seed_products():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    db = Session()
    db.add_all(
        [
            Product(
                id="p_audio_001",
                title="星云主动降噪耳机 通勤长续航",
                category="数码电子",
                brand="Nebula",
                price=699,
                description="适合地铁通勤，主动降噪，佩戴舒适。",
                specs_json='{"noise_canceling": "ANC", "battery_life": "40h"}',
                rating=4.8,
                sales=1500,
                stock=20,
            ),
            Product(
                id="p_pad_001",
                title="轻薄学习平板",
                category="数码电子",
                brand="Slate",
                price=1999,
                description="适合网课和手写笔记。",
                specs_json='{"screen": "11 inch"}',
                rating=4.7,
                sales=1200,
                stock=10,
            ),
            Product(
                id="p_food_001",
                title="低糖早餐麦片",
                category="食品饮料",
                brand="Morning",
                price=59,
                description="低糖饱腹早餐。",
                specs_json='{"flavor": "grain"}',
                rating=4.5,
                sales=800,
                stock=30,
            ),
        ]
    )
    db.commit()
    return db
