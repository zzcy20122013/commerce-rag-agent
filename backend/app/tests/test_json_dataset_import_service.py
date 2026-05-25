from app.agents.shopping_guide import product_to_card, sort_products_for_memory
from app.models.tables import Product
from app.retrieval.text_index import product_to_text
from app.services.json_dataset_import_service import build_knowledge_chunks, build_product_specs
from app.models.db import Base
from app.models.tables import Document
from app.services.index_job_service import rebuild_knowledge_docs_index
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


def test_build_knowledge_chunks_splits_marketing_faq_and_reviews_with_metadata() -> None:
    payload = {
        "product_id": "p_beauty_001",
        "title": "修护精华",
        "brand": "测试品牌",
        "category": "美妆护肤",
        "sub_category": "精华",
    }
    knowledge = {
        "marketing_description": "主打夜间修护和保湿，适合熬夜后暗沉。",
        "official_faq": [
            {"question": "敏感肌能用吗？", "answer": "建议先做耳后测试。"},
            {"question": "怎么用？", "answer": "洁面后使用。"},
        ],
        "user_reviews": [
            {"nickname": "李小米", "rating": 1, "content": "敏感肌用了刺痛。"},
            {"nickname": "张雅静", "rating": 5, "content": "熬夜后用着很稳。"},
        ],
    }

    chunks = build_knowledge_chunks(payload, knowledge)

    assert [chunk["metadata"]["chunk_type"] for chunk in chunks] == [
        "marketing_description",
        "official_faq",
        "official_faq",
        "user_review",
        "user_review",
    ]
    assert all(chunk["metadata"]["product_id"] == "p_beauty_001" for chunk in chunks)
    assert chunks[0]["metadata"]["brand"] == "测试品牌"
    assert chunks[1]["metadata"]["question"] == "敏感肌能用吗？"
    assert chunks[3]["metadata"]["rating"] == 1
    assert "敏感肌用了刺痛" in chunks[3]["text"]


def test_rebuild_knowledge_docs_index_preserves_product_chunk_metadata(monkeypatch) -> None:
    captured = {}

    class FakeDocumentIndex:
        def __init__(self, *, chroma_path=None):
            self.chroma_path = chroma_path

        def rebuild_chunks(self, chunks):
            captured["chunks"] = chunks

    monkeypatch.setattr("app.services.index_job_service.DocumentIndex", FakeDocumentIndex)

    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    TestingSession = sessionmaker(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = TestingSession()
    try:
        db.add(
            Document(
                id="doc_p_beauty_001_review_0",
                source_file="p_beauty_001:3",
                doc_type="product_knowledge",
                category="美妆护肤",
                version="dataset_v1",
                metadata_json=(
                    '{"product_id":"p_beauty_001","chunk_type":"user_review",'
                    '"rating":1,"text":"修护精华 用户评价：敏感肌用了刺痛。"}'
                ),
            )
        )
        db.commit()

        count = rebuild_knowledge_docs_index(db)

        assert count == 1
        chunk = captured["chunks"][0]
        assert chunk["text"] == "修护精华 用户评价：敏感肌用了刺痛。"
        assert chunk["metadata"]["product_id"] == "p_beauty_001"
        assert chunk["metadata"]["chunk_type"] == "user_review"
        assert chunk["metadata"]["rating"] == 1
    finally:
        db.close()


def test_product_specs_include_sku_options_and_review_risk_summary() -> None:
    skus = [
        {"properties": {"容量": "30ml 经典装"}, "price": 720},
        {"properties": {"容量": "50ml 加大装"}, "price": 980},
    ]
    knowledge = {
        "official_faq": [{"question": "怎么选", "answer": "按用量选"}],
        "user_reviews": [
            {"rating": 1, "content": "敏感肌用了刺痛，脸颊泛红。"},
            {"rating": 5, "content": "熬夜后用着很稳。"},
        ],
    }

    specs = build_product_specs(sub_category="精华", skus=skus, base_price=720, knowledge=knowledge)

    assert specs["sku_options"] == ["30ml 经典装", "50ml 加大装"]
    assert specs["price_range"] == {"min": 720, "max": 980}
    assert specs["review_summary"]["negative_review_count"] == 1
    assert "敏感肌" in specs["review_summary"]["negative_keywords"]

    product = Product(
        id="p_beauty_001",
        title="修护精华",
        category="美妆护肤",
        brand="测试品牌",
        price=720,
        description="主打修护",
        specs_json='{"sku_options":["30ml 经典装","50ml 加大装"],"review_summary":{"negative_keywords":["敏感肌"]}}',
        rating=4.0,
        sales=100,
        stock=10,
        image_url="",
    )
    text = product_to_text(product)
    assert "50ml 加大装" in text
    assert "敏感肌" in text


def test_review_risk_can_lower_sensitive_skin_recommendation_rank() -> None:
    risky = Product(
        id="p_risky",
        title="高功效修护精华",
        category="美妆护肤",
        brand="测试品牌",
        price=199,
        description="适合敏感肌修护",
        specs_json='{"review_summary":{"negative_review_count":3,"negative_keywords":["敏感肌","刺痛"]}}',
        rating=4.9,
        sales=2000,
        stock=10,
        image_url="",
    )
    gentle = Product(
        id="p_gentle",
        title="温和修护精华",
        category="美妆护肤",
        brand="测试品牌",
        price=219,
        description="温和保湿，适合敏感肌",
        specs_json='{"review_summary":{"negative_review_count":0,"negative_keywords":[]}}',
        rating=4.4,
        sales=800,
        stock=10,
        image_url="",
    )

    ranked = sort_products_for_memory(
        [risky, gentle],
        {"category": "美妆护肤", "preferences": ["敏感肌友好"]},
        query="敏感肌想要温和不刺痛的精华",
    )

    assert ranked[0].id == "p_gentle"


def test_product_card_contains_explainable_evidence_sources() -> None:
    product = Product(
        id="p_beauty_001",
        title="温和修护精华",
        category="美妆护肤",
        brand="测试品牌",
        price=219,
        description="温和保湿，适合敏感肌",
        specs_json='{"review_summary":{"negative_review_count":1,"negative_keywords":["刺痛"]}}',
        rating=4.6,
        sales=1200,
        stock=8,
        image_url="",
    )

    card = product_to_card(
        product,
        {"budget_max": 300, "preferences": ["敏感肌友好"]},
        rank=1,
    )

    evidence = card["evidence"]
    assert any(item["source"] == "价格/销量/评分" for item in evidence)
    assert any(item["source"] == "用户评价" for item in evidence)
    assert card["source_summary"] == "推荐依据：价格/销量/评分、用户评价、商品规格"
    assert "商品库结构化字段" not in card["source_summary"]
