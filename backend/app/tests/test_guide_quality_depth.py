import json

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.agents.guide_quality import evaluate_guide_quality
from app.agents.shopping_guide import product_to_card, shopping_guide_node
from app.llm.generation import GenerationResult
from app.models.db import Base
from app.models.tables import Product
from app.services.business_rules import rule_dict


def test_guide_quality_identifies_missing_category_slots() -> None:
    quality = evaluate_guide_quality(
        memory={"category": "服饰运动", "subcategory": "鞋", "budget_max": 300},
        cards=[],
        retrieval_trace={"low_confidence": True, "confidence": 0.0},
        query="推荐一双鞋",
    )

    assert quality["category_sop"]["sop_name"] == "运动鞋导购SOP"
    assert "use_cases" in quality["missing_slots"]
    assert "preferences" in quality["missing_slots"]
    assert "low_confidence_retrieval" in quality["quality_flags"]
    assert quality["needs_clarification"] is True


def test_category_sop_can_be_loaded_from_commerce_rules() -> None:
    subcategory_sops = rule_dict("guide_sops", "subcategories")
    quality = evaluate_guide_quality(
        memory={"category": "美妆护肤", "subcategory": "防晒", "budget_max": 100},
        cards=[],
        retrieval_trace={},
        query="推荐日常通勤防晒",
    )

    assert "防晒" in subcategory_sops
    assert quality["category_sop"]["sop_name"] == "防晒导购SOP"
    assert "防护" in quality["evidence_priorities"]
    assert "肤感" in quality["evidence_priorities"]


def test_product_card_exposes_review_insight_as_structured_evidence() -> None:
    product = _shoe(
        specs={
            "review_summary": {
                "positive_keywords": ["脚感软", "耐穿"],
                "negative_keywords": ["偏硬"],
                "negative_review_count": 2,
                "representative_negative_reviews": ["鞋面偏硬，需要磨合"],
            }
        }
    )

    card = product_to_card(product, {"subcategory": "鞋", "preferences": ["耐穿"]}, rank=1)

    assert card["review_insight"]["positive_keywords"] == ["脚感软", "耐穿"]
    assert card["review_insight"]["negative_keywords"] == ["偏硬"]
    assert any(item["source"] == "用户评价正向" and "脚感软" in item["detail"] for item in card["evidence"])
    assert any("评价提醒" in reason for reason in card["reasons"])


def test_review_insight_adds_dimension_judgement_from_rules() -> None:
    product = Product(
        id="p_pad_001",
        title="学习护眼手写平板",
        category="数码电子",
        brand="Slate",
        price=2199,
        description="适合网课和记笔记。",
        specs_json=json.dumps(
            {
                "review_summary": {
                    "positive_keywords": ["手写流畅", "屏幕护眼"],
                    "representative_positive_reviews": ["手写笔延迟低，网课视频也清晰，屏幕护眼。"],
                }
            },
            ensure_ascii=False,
        ),
        rating=4.7,
        sales=1300,
        stock=8,
        image_url="",
    )

    card = product_to_card(product, {"subcategory": "平板", "use_cases": ["记笔记"]}, rank=1)

    assert card["review_insight"]["dimensions"]["手写记笔记"] == "反馈较多"
    assert card["review_insight"]["dimensions"]["屏幕"] == "反馈较多"


def test_shopping_trace_includes_guide_quality(monkeypatch) -> None:
    def fake_retrieve(db, candidates, memory, query):
        return candidates, {"retrieval_mode": "fake", "low_confidence": True, "confidence": 0.0}

    def fake_generate(*, query, cards, memory, fallback, client=None):
        return GenerationResult(content=fallback, llm_enabled=False, llm_error="test")

    monkeypatch.setattr("app.agents.shopping_guide.hybrid_retrieve_and_rerank", fake_retrieve)
    monkeypatch.setattr("app.agents.shopping_guide.generate_shopping_result", fake_generate)

    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    TestingSession = sessionmaker(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = TestingSession()
    try:
        db.add(_shoe())
        db.commit()

        result = shopping_guide_node(db)(
            {
                "query": "推荐一双鞋",
                "memory": {"category": "服饰运动", "subcategory": "鞋", "budget_max": 300},
                "trace": [],
            }
        )

        guide_quality = result["trace"][-1]["guide_quality"]
        assert guide_quality["category_sop"]["sop_name"] == "运动鞋导购SOP"
        assert "use_cases" in guide_quality["missing_slots"]
        assert "low_confidence_retrieval" in guide_quality["quality_flags"]
    finally:
        db.close()


def _shoe(specs: dict | None = None) -> Product:
    return Product(
        id="p_shoe_001",
        title="安踏轻便耐穿通勤跑鞋",
        category="服饰运动",
        brand="安踏",
        price=269,
        description="适合日常走路，缓震舒适。",
        specs_json=json.dumps(specs or {"适用场景": "通勤"}, ensure_ascii=False),
        rating=4.6,
        sales=1200,
        stock=10,
        image_url="",
    )
