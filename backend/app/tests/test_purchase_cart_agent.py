from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.agents.purchase import purchase_help_node
from app.models.db import Base
from app.models.tables import Product
from app.services.cart_service import list_cart_items


def test_purchase_agent_adds_requested_categories_from_last_recommendations() -> None:
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    TestingSession = sessionmaker(bind=engine)
    Base.metadata.create_all(bind=engine)

    db = TestingSession()
    try:
        products = [
            _product("p_pants_001", "黑色通勤直筒裤", 199),
            _product("p_pants_002", "轻薄运动短裤", 129),
            _product("p_skirt_001", "法式半身裙", 169),
            _product("p_shoes_001", "轻便通勤鞋", 269),
        ]
        db.add_all(products)
        db.commit()

        node = purchase_help_node(db)
        result = node(
            {
                "query": "帮我把刚才你推荐的两个裤子和一个裙子都加入购物车",
                "memory": {"last_product_ids": [product.id for product in products]},
                "trace": [],
            }
        )

        cart_items = list_cart_items(db)
        assert result["intent"] == "purchase_help"
        assert "已加入购物车" in result["answer"]
        assert [item["product"]["id"] for item in cart_items] == ["p_pants_001", "p_pants_002", "p_skirt_001"]
        assert [item["quantity"] for item in cart_items] == [1, 1, 1]
    finally:
        db.close()


def test_purchase_agent_can_view_update_and_remove_cart_items() -> None:
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    TestingSession = sessionmaker(bind=engine)
    Base.metadata.create_all(bind=engine)

    db = TestingSession()
    try:
        db.add_all([
            _product("p_pants_001", "黑色通勤直筒裤", 199),
            _product("p_skirt_001", "法式半身裙", 169),
        ])
        db.commit()

        node = purchase_help_node(db)
        node({"query": "把刚才推荐的都加入购物车", "memory": {"last_product_ids": ["p_pants_001", "p_skirt_001"]}, "trace": []})
        updated = node({"query": "把第一个数量改成 2", "memory": {}, "trace": []})
        viewed = node({"query": "查看购物车", "memory": {}, "trace": []})
        removed = node({"query": "删除第二个", "memory": {}, "trace": []})

        assert "数量改成 2" in updated["answer"]
        assert "黑色通勤直筒裤 x 2" in viewed["answer"]
        assert "已从购物车删除" in removed["answer"]
        assert [item["product"]["id"] for item in list_cart_items(db)] == ["p_pants_001"]
    finally:
        db.close()


def test_purchase_agent_prefers_explicit_product_id_over_memory() -> None:
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    TestingSession = sessionmaker(bind=engine)
    Base.metadata.create_all(bind=engine)

    db = TestingSession()
    try:
        db.add_all([
            _product("p_pants_001", "黑色通勤直筒裤", 199),
            _product("p_skirt_001", "法式半身裙", 169),
        ])
        db.commit()

        node = purchase_help_node(db)
        node(
            {
                "query": "把 p_skirt_001 加入购物车",
                "memory": {"last_product_ids": ["p_pants_001"]},
                "trace": [],
            }
        )

        assert [item["product"]["id"] for item in list_cart_items(db)] == ["p_skirt_001"]
    finally:
        db.close()


def test_purchase_agent_adds_requested_quantity_for_single_product() -> None:
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    TestingSession = sessionmaker(bind=engine)
    Base.metadata.create_all(bind=engine)

    db = TestingSession()
    try:
        db.add(_product("p_food_020", "日清合味道海鲜风味杯面", 69))
        db.commit()

        node = purchase_help_node(db)
        result = node(
            {
                "query": "把刚才那个杯面加入 100 件",
                "memory": {"last_product_ids": ["p_food_020"]},
                "trace": [],
            }
        )

        cart_items = list_cart_items(db)
        assert "已加入购物车" in result["answer"]
        assert cart_items[0]["product"]["id"] == "p_food_020"
        assert cart_items[0]["quantity"] == 100
    finally:
        db.close()


def _product(product_id: str, title: str, price: int) -> Product:
    return Product(
        id=product_id,
        title=title,
        category="服饰运动",
        brand="测试品牌",
        price=price,
        description=title,
        rating=4.6,
        sales=1000,
        stock=10,
        image_url="",
    )
