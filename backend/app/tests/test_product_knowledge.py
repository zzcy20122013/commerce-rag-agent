from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.agents.product_knowledge import product_knowledge_node
from app.models.db import Base
from app.models.tables import Product


def test_product_knowledge_uses_vector_knowledge_hits(monkeypatch) -> None:
    class FakeDocumentIndex:
        def __init__(self, *, chroma_path=None):
            self.chroma_path = chroma_path

        def search(self, query, *, limit=5):
            return [
                {
                    "id": "doc_review_0",
                    "text": "修护精华 用户评价：李小米（1星）：敏感肌用了刺痛。",
                    "metadata": {"product_id": "p_beauty_001", "chunk_type": "user_review", "rating": 1},
                    "distance": 0.1,
                }
            ]

    monkeypatch.setattr("app.agents.product_knowledge.DocumentIndex", FakeDocumentIndex)

    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    TestingSession = sessionmaker(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = TestingSession()
    try:
        db.add(
            Product(
                id="p_beauty_001",
                title="修护精华",
                category="美妆护肤",
                brand="测试品牌",
                price=199,
                description="主打修护保湿",
                specs_json="{}",
                rating=4.2,
                sales=100,
                stock=10,
                image_url="",
            )
        )
        db.commit()

        result = product_knowledge_node(db)(
            {
                "query": "p_beauty_001 敏感肌会刺痛吗",
                "memory": {},
                "trace": [],
            }
        )

        assert "敏感肌用了刺痛" in result["answer"]
        assert result["retrieved_items"][1]["metadata"]["chunk_type"] == "user_review"
        assert result["trace"][-1]["retrieval_mode"] == "vector_knowledge_docs"
    finally:
        db.close()
