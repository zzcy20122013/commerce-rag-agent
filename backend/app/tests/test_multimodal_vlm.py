from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.agents.multimodal import run_multimodal_search
from app.models.db import Base
from app.models.tables import Product
from app.services.vlm_service import VisualAttributes, VisionAnalysisResult


class FakeImageIndex:
    def ensure_product_images_indexed(self, db: Session) -> None:
        return

    def search_by_image(self, image_path: str, *, limit: int = 24) -> list[dict]:
        return [
            {
                "id": "p_shoe:image",
                "text": "黑色网布缓震跑鞋 运动 通勤",
                "metadata": {
                    "product_id": "p_shoe",
                    "title": "黑色网布缓震跑鞋",
                    "category": "鞋",
                    "brand": "RunFast",
                    "price": 399,
                    "rating": 4.8,
                    "sales": 900,
                    "stock": 20,
                },
                "distance": 0.1,
                "image_similarity": 0.9,
            },
            {
                "id": "p_bag:image",
                "text": "黑色通勤背包",
                "metadata": {
                    "product_id": "p_bag",
                    "title": "黑色通勤背包",
                    "category": "背包",
                    "brand": "DailyCarry",
                    "price": 199,
                    "rating": 4.6,
                    "sales": 400,
                    "stock": 15,
                },
                "distance": 0.2,
                "image_similarity": 0.8,
            },
        ]


class FakeVlmService:
    def analyze_image(self, image_path: str, *, query: str) -> VisionAnalysisResult:
        return VisionAnalysisResult(
            enabled=True,
            attributes=VisualAttributes(
                category="跑鞋",
                colors=["黑色"],
                materials=["网布"],
                style=["缓震", "运动"],
                use_cases=["跑步", "通勤"],
                search_terms=["黑色网布跑鞋", "缓震跑鞋"],
                confidence=0.9,
            ),
        )


class FakeDisabledVlmService:
    def analyze_image(self, image_path: str, *, query: str) -> VisionAnalysisResult:
        return VisionAnalysisResult(enabled=False, error="missing_vision_config")


def test_multimodal_search_uses_vlm_attributes_in_trace_answer_and_reasons() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestingSession = sessionmaker(bind=engine)
    db = TestingSession()
    db.add_all(
        [
            Product(
                id="p_shoe",
                title="黑色网布缓震跑鞋",
                category="鞋",
                brand="RunFast",
                price=399,
                description="适合跑步通勤的黑色网布缓震跑鞋",
                rating=4.8,
                sales=900,
                stock=20,
                image_url="/static/product_images/p_shoe.png",
            ),
            Product(
                id="p_bag",
                title="黑色通勤背包",
                category="背包",
                brand="DailyCarry",
                price=199,
                description="日常通勤背包",
                rating=4.6,
                sales=400,
                stock=15,
                image_url="/static/product_images/p_bag.png",
            ),
        ]
    )
    db.commit()

    result = run_multimodal_search(
        db,
        query="找类似的，500以内",
        image_path="upload.jpg",
        image_index=FakeImageIndex(),
        vlm_service=FakeVlmService(),
    )

    assert result["intent"] == "multimodal_search"
    assert result["product_cards"][0]["product_id"] == "p_shoe"
    assert "我看这张图更像是跑鞋" in result["answer"]
    assert "图片判断：跑鞋" in result["product_cards"][0]["reasons"]
    assert "VLM" not in result["answer"]
    assert all("VLM" not in reason for reason in result["product_cards"][0]["reasons"])
    trace = result["trace"][0]
    assert trace["vlm_enabled"] is True
    assert trace["vlm_attributes"]["category"] == "跑鞋"
    assert "缓震跑鞋" in trace["visual_terms"]


def test_multimodal_search_uses_natural_copy_when_vlm_is_disabled() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestingSession = sessionmaker(bind=engine)
    db = TestingSession()
    db.add(
        Product(
            id="p_shoe",
            title="黑色网布缓震跑鞋",
            category="鞋",
            brand="RunFast",
            price=399,
            description="适合跑步通勤的黑色网布缓震跑鞋",
            rating=4.8,
            sales=900,
            stock=20,
            image_url="/static/product_images/p_shoe.png",
        )
    )
    db.commit()

    result = run_multimodal_search(
        db,
        query="找类似的，500以内",
        image_path="upload.jpg",
        image_index=FakeImageIndex(),
        vlm_service=FakeDisabledVlmService(),
    )

    assert "我先按这张图的外观帮你找相似款" in result["answer"]
    assert "VLM" not in result["answer"]


def test_multimodal_search_does_not_claim_missing_price_or_scene_constraints() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestingSession = sessionmaker(bind=engine)
    db = TestingSession()
    db.add(
        Product(
            id="p_shoe",
            title="黑色网布缓震跑鞋",
            category="鞋",
            brand="RunFast",
            price=399,
            description="适合跑步通勤的黑色网布缓震跑鞋",
            rating=4.8,
            sales=900,
            stock=20,
            image_url="/static/product_images/p_shoe.png",
        )
    )
    db.commit()

    result = run_multimodal_search(
        db,
        query="请按这张图片找相似商品",
        image_path="upload.jpg",
        image_index=FakeImageIndex(),
        vlm_service=FakeDisabledVlmService(),
    )

    assert "价格" not in result["answer"]
    assert "场景约束" not in result["answer"]
    assert "相似" in result["answer"]
