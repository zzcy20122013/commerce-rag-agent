from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.agents.intent_router import classify_intent
from app.agents.shopping_guide import build_recommendation_answer, merge_memory, shopping_guide_node
from app.api.chat import apply_negative_constraints_to_memory
from app.llm.generation import GenerationResult
from app.models.db import Base
from app.models.tables import Product
from app.services.constraint_parser import parse_constraints


def test_other_brand_question_is_a_multiturn_followup() -> None:
    result = classify_intent("有其他品牌吗")

    assert result.intent == "clarification"


def test_common_followup_phrases_keep_shopping_context() -> None:
    for query in [
        "换个牌子看看",
        "有没有国产的",
        "还有便宜点的吗",
        "300 真不能超",
        "别给我这个牌子",
        "不要刚才那个品牌",
        "如果我更看重耐穿呢",
    ]:
        result = classify_intent(query)

        assert result.intent in {"clarification", "shopping_guide"}
        assert result.intent != "chitchat"


def test_recommendation_answer_hides_internal_reason_expressions() -> None:
    answer = build_recommendation_answer(
        [
            {
                "title": "vivo Pad 6 Pro 12.1英寸高刷全面屏学习娱乐多任务办公平板电脑",
                "price": 3299,
                "reasons": ["预算内：3299<=3500", "适合记笔记", "销量较高：1750"],
            },
            {
                "title": "小米平板 8 Pro 12.1英寸高刷大屏影音娱乐学习办公平板电脑",
                "price": 3299,
                "reasons": ["预算内：3299<=3500", "适合记笔记"],
            },
        ],
        {"budget_max": 3500, "category": "数码电子", "subcategory": "平板"},
    )

    assert "<=" not in answer
    assert "3299<=3500" not in answer
    assert "3500 元预算内" in answer
    assert "适合记笔记" in answer


def test_other_brand_followup_excludes_last_recommendations() -> None:
    memory = merge_memory(
        {
            "category": "服饰运动",
            "subcategory": "鞋",
            "budget_max": 300,
            "last_product_ids": ["p_shoe_001", "p_shoe_002"],
        },
        {},
        "有其他品牌吗",
    )

    assert memory["category"] == "服饰运动"
    assert memory["subcategory"] == "鞋"
    assert memory["budget_max"] == 300
    assert memory["exclude_product_ids"] == ["p_shoe_001", "p_shoe_002"]


def test_strict_budget_followup_keeps_budget_and_blocks_over_budget_cards(monkeypatch) -> None:
    def fake_retrieve(db, candidates, memory, query):
        return candidates, {"retrieval_mode": "fake", "sqlite_candidates": len(candidates), "chroma_hits": []}

    monkeypatch.setattr("app.agents.shopping_guide.hybrid_retrieve_and_rerank", fake_retrieve)

    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    TestingSession = sessionmaker(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = TestingSession()
    try:
        db.add_all(
            [
                _shoe("p_shoe_001", "Nike Air Zoom Pegasus 41 男子通勤跑鞋", "Nike", 899),
                _shoe("p_shoe_002", "adidas Ultraboost 5 男子缓震通勤鞋", "adidas", 1399),
            ]
        )
        db.commit()

        result = shopping_guide_node(db)(
            {
                "query": "300 真不能超",
                "memory": {
                    "category": "服饰运动",
                    "subcategory": "鞋",
                    "budget_max": 300,
                    "use_cases": ["通勤"],
                    "last_product_ids": ["p_shoe_001", "p_shoe_002"],
                },
                "trace": [],
            }
        )

        assert result["no_exact_match"] is True
        assert result["product_cards"] == []
        assert "没有找到严格符合" in result["answer"]
    finally:
        db.close()


def test_deictic_brand_exclusion_uses_last_top_product_brand() -> None:
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    TestingSession = sessionmaker(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = TestingSession()
    try:
        db.add_all(
            [
                _shoe("p_shoe_001", "Nike Air Zoom Pegasus 41 男子通勤跑鞋", "Nike", 899),
                _shoe("p_shoe_002", "adidas Ultraboost 5 男子缓震通勤鞋", "adidas", 1399),
            ]
        )
        db.commit()

        memory = apply_negative_constraints_to_memory(
            {"last_product_ids": ["p_shoe_001", "p_shoe_002"]},
            parse_constraints("别给我这个牌子"),
            db=db,
        )

        assert memory["exclusions"][0]["kind"] == "exclude_brand"
        assert memory["exclusions"][0]["value"] == "Nike"
    finally:
        db.close()


def test_domestic_brand_followup_prefers_domestic_products() -> None:
    memory = merge_memory(
        {
            "category": "服饰运动",
            "subcategory": "鞋",
            "budget_max": 1500,
            "last_product_ids": ["p_shoe_001"],
        },
        {},
        "有没有国产的",
    )

    assert "国产品牌" in memory["preferences"]


def test_durability_followup_adds_preference_without_losing_context() -> None:
    memory = merge_memory(
        {
            "category": "服饰运动",
            "subcategory": "鞋",
            "budget_max": 300,
            "use_cases": ["通勤"],
        },
        {},
        "如果我更看重耐穿呢",
    )

    assert memory["category"] == "服饰运动"
    assert memory["subcategory"] == "鞋"
    assert memory["budget_max"] == 300
    assert memory["use_cases"] == ["通勤"]
    assert "耐穿" in memory["preferences"]


def test_shopping_trace_exposes_effective_constraints_and_memory_snapshot(monkeypatch) -> None:
    def fake_retrieve(db, candidates, memory, query):
        return candidates, {"retrieval_mode": "fake", "sqlite_candidates": len(candidates), "chroma_hits": []}

    monkeypatch.setattr("app.agents.shopping_guide.hybrid_retrieve_and_rerank", fake_retrieve)

    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    TestingSession = sessionmaker(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = TestingSession()
    try:
        db.add_all(
            [
                _shoe("p_shoe_001", "Nike Air Zoom Pegasus 41 男子通勤跑鞋", "Nike", 899),
                _shoe("p_shoe_002", "安踏轻便耐穿通勤跑鞋", "安踏", 269),
            ]
        )
        db.commit()

        result = shopping_guide_node(db)(
            {
                "query": "如果我更看重耐穿呢",
                "memory": {
                    "category": "服饰运动",
                    "subcategory": "鞋",
                    "budget_max": 300,
                    "use_cases": ["通勤"],
                    "last_product_ids": ["p_shoe_001"],
                },
                "trace": [],
            }
        )

        trace = result["trace"][-1]
        assert trace["effective_constraints"]["budget_max"] == 300
        assert trace["effective_constraints"]["subcategory"] == "鞋"
        assert trace["memory_snapshot"]["use_cases"] == ["通勤"]
        assert "耐穿" in trace["memory_snapshot"]["preferences"]
        assert trace["memory_snapshot"]["last_product_ids"] == ["p_shoe_001"]
    finally:
        db.close()


def test_domestic_brand_preference_ranks_domestic_product_first() -> None:
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    TestingSession = sessionmaker(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = TestingSession()
    try:
        db.add_all(
            [
                _shoe("p_shoe_001", "Nike Air Zoom Pegasus 41 男子通勤跑鞋", "Nike", 899),
                _shoe("p_shoe_002", "安踏轻便通勤跑鞋", "安踏", 699),
            ]
        )
        db.commit()

        result = shopping_guide_node(db)(
            {
                "query": "有没有国产的",
                "memory": {
                    "category": "服饰运动",
                    "subcategory": "鞋",
                    "budget_max": 1500,
                    "use_cases": ["通勤"],
                },
                "trace": [],
            }
        )

        assert result["product_cards"][0]["product_id"] == "p_shoe_002"
        assert "国产品牌" in result["product_cards"][0]["reasons"]
    finally:
        db.close()


def test_deictic_brand_exclusion_filters_that_brand(monkeypatch) -> None:
    def fake_retrieve(db, candidates, memory, query):
        return candidates, {"retrieval_mode": "fake", "sqlite_candidates": len(candidates), "chroma_hits": []}

    monkeypatch.setattr("app.agents.shopping_guide.hybrid_retrieve_and_rerank", fake_retrieve)

    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    TestingSession = sessionmaker(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = TestingSession()
    try:
        db.add_all(
            [
                _shoe("p_shoe_001", "Nike Air Zoom Pegasus 41 男子通勤跑鞋", "Nike", 899),
                _shoe("p_shoe_002", "安踏轻便通勤跑鞋", "安踏", 699),
            ]
        )
        db.commit()
        memory = apply_negative_constraints_to_memory(
            {
                "category": "服饰运动",
                "subcategory": "鞋",
                "budget_max": 1500,
                "last_product_ids": ["p_shoe_001", "p_shoe_002"],
            },
            parse_constraints("别给我这个牌子"),
            db=db,
        )

        result = shopping_guide_node(db)({"query": "别给我这个牌子", "memory": memory, "trace": []})

        assert [card["product_id"] for card in result["product_cards"]] == ["p_shoe_002"]
    finally:
        db.close()


def test_no_exact_budget_match_limits_over_budget_cards(monkeypatch) -> None:
    captured_cards = []

    def fake_retrieve(db, candidates, memory, query):
        return candidates, {"retrieval_mode": "fake", "sqlite_candidates": len(candidates), "chroma_hits": []}

    def fake_generate(*, query, cards, memory, fallback, client=None):
        captured_cards.extend(cards)
        return GenerationResult(content=fallback, llm_enabled=False, llm_error="test")

    monkeypatch.setattr("app.agents.shopping_guide.hybrid_retrieve_and_rerank", fake_retrieve)
    monkeypatch.setattr("app.agents.shopping_guide.generate_shopping_result", fake_generate)

    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    TestingSession = sessionmaker(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = TestingSession()
    try:
        db.add_all(
            [
                _shoe("p_shoe_001", "Nike Air Zoom Pegasus 41 男子通勤跑鞋", "Nike", 899),
                _shoe("p_shoe_002", "adidas Ultraboost 5 男子缓震通勤鞋", "adidas", 1399),
                _shoe("p_shoe_003", "特步 160X 6.0 PRO 碳板竞速跑鞋", "特步", 999),
            ]
        )
        db.commit()

        result = shopping_guide_node(db)({"query": "推荐 300 以内通勤鞋", "memory": {}, "trace": []})

        assert result["no_exact_match"] is True
        assert len(result["product_cards"]) == 2
        assert captured_cards == result["product_cards"]
        assert all(card["price"] > 300 for card in result["product_cards"])
    finally:
        db.close()


def _shoe(product_id: str, title: str, brand: str, price: int) -> Product:
    return Product(
        id=product_id,
        title=title,
        category="服饰运动",
        brand=brand,
        price=price,
        description="适合通勤和日常走路，缓震舒适。",
        specs_json='{"适用场景":"通勤"}',
        rating=4.2,
        sales=1400,
        stock=10,
        image_url="",
    )
