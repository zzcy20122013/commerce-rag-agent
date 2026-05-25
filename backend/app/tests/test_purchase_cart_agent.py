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


def test_purchase_agent_can_clear_cart() -> None:
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
        result = node({"query": "清空购物车", "memory": {"last_product_ids": ["p_pants_001"]}, "trace": []})

        assert "已清空购物车" in result["answer"]
        assert list_cart_items(db) == []
    finally:
        db.close()


def test_purchase_agent_guides_checkout_to_confirm_shipping_address() -> None:
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    TestingSession = sessionmaker(bind=engine)
    Base.metadata.create_all(bind=engine)

    db = TestingSession()
    try:
        db.add(_product("p_pants_001", "黑色通勤直筒裤", 199))
        db.commit()

        node = purchase_help_node(db)
        node({"query": "把 p_pants_001 加入购物车", "memory": {}, "trace": []})
        result = node({"query": "怎么下单", "memory": {}, "trace": []})

        assert "确认收货地址" in result["answer"]
        assert "当前购物车" in result["answer"]
    finally:
        db.close()


def test_purchase_agent_treats_common_view_phrases_as_view_only() -> None:
    for phrase in ["看看购物车", "打开购物车", "购物车"]:
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
            result = node({"query": phrase, "memory": {"last_product_ids": ["p_pants_001"]}, "trace": []})

            assert "当前购物车" in result["answer"]
            assert [item["quantity"] for item in list_cart_items(db)] == [1, 1]
        finally:
            db.close()


def test_purchase_agent_treats_common_clear_phrases_as_clear() -> None:
    for phrase in ["把购物车清掉", "购物车里的都删掉", "全部删掉"]:
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
            result = node({"query": phrase, "memory": {"last_product_ids": ["p_pants_001"]}, "trace": []})

            assert "已清空购物车" in result["answer"]
            assert list_cart_items(db) == []
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


def test_purchase_agent_selects_named_brand_from_recent_recommendations() -> None:
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    TestingSession = sessionmaker(bind=engine)
    Base.metadata.create_all(bind=engine)

    db = TestingSession()
    try:
        db.add_all([
            _product("p_digital_019", "vivo Pad 6 Pro 12.1英寸平板", 3299, brand="vivo", category="数码电子"),
            _product("p_digital_011", "小米平板 8 Pro 12.1英寸平板", 3299, brand="小米", category="数码电子"),
        ])
        db.commit()

        node = purchase_help_node(db)
        result = node(
            {
                "query": "把小米加入购物车",
                "memory": {"last_product_ids": ["p_digital_019", "p_digital_011"]},
                "trace": [],
            }
        )

        cart_items = list_cart_items(db)
        assert "已加入购物车" in result["answer"]
        assert [item["product"]["id"] for item in cart_items] == ["p_digital_011"]
    finally:
        db.close()


def test_purchase_agent_adds_requested_quantity_for_single_product() -> None:
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    TestingSession = sessionmaker(bind=engine)
    Base.metadata.create_all(bind=engine)

    db = TestingSession()
    try:
        db.add(_product("p_food_020", "日清合味道海鲜风味杯面", 69, stock=120))
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


def test_purchase_agent_does_not_treat_quantity_as_selection_count() -> None:
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    TestingSession = sessionmaker(bind=engine)
    Base.metadata.create_all(bind=engine)

    db = TestingSession()
    try:
        products = [
            _product("p_food_020", "日清合味道海鲜风味杯面", 69),
            _product("p_food_021", "雀巢速溶咖啡", 60),
            _product("p_food_022", "黑咖啡冻干粉", 42),
        ]
        db.add_all(products)
        db.commit()

        node = purchase_help_node(db)
        result = node(
            {
                "query": "这个加 3 件",
                "memory": {"last_product_ids": [product.id for product in products]},
                "trace": [],
            }
        )

        cart_items = list_cart_items(db)
        assert "已加入购物车" in result["answer"]
        assert [item["product"]["id"] for item in cart_items] == ["p_food_020"]
        assert [item["quantity"] for item in cart_items] == [3]
    finally:
        db.close()


def test_purchase_agent_adds_first_two_recommendations_with_quantity() -> None:
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    TestingSession = sessionmaker(bind=engine)
    Base.metadata.create_all(bind=engine)

    db = TestingSession()
    try:
        products = [
            _product("p_food_020", "日清合味道海鲜风味杯面", 69),
            _product("p_food_021", "雀巢速溶咖啡", 60),
            _product("p_food_022", "黑咖啡冻干粉", 42),
        ]
        db.add_all(products)
        db.commit()

        node = purchase_help_node(db)
        result = node(
            {
                "query": "这两个都加 3 件",
                "memory": {"last_product_ids": [product.id for product in products]},
                "trace": [],
            }
        )

        cart_items = list_cart_items(db)
        assert "已加入购物车" in result["answer"]
        assert [item["product"]["id"] for item in cart_items] == ["p_food_020", "p_food_021"]
        assert [item["quantity"] for item in cart_items] == [3, 3]
    finally:
        db.close()


def test_purchase_agent_updates_cart_item_by_product_word() -> None:
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    TestingSession = sessionmaker(bind=engine)
    Base.metadata.create_all(bind=engine)

    db = TestingSession()
    try:
        db.add_all([
            _product("p_food_020", "日清合味道海鲜风味杯面", 69),
            _product("p_beauty_006", "巴黎欧莱雅防晒隔离露", 170),
        ])
        db.commit()

        node = purchase_help_node(db)
        node({"query": "把刚才推荐的都加入购物车", "memory": {"last_product_ids": ["p_food_020", "p_beauty_006"]}, "trace": []})
        result = node({"query": "把防晒那个改成 2 瓶", "memory": {}, "trace": []})

        cart_items = list_cart_items(db)
        assert "防晒" in result["answer"]
        assert [item["quantity"] for item in cart_items] == [1, 2]
    finally:
        db.close()


def test_purchase_agent_removes_cart_item_by_recent_position_phrase() -> None:
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    TestingSession = sessionmaker(bind=engine)
    Base.metadata.create_all(bind=engine)

    db = TestingSession()
    try:
        db.add_all([
            _product("p_food_020", "日清合味道海鲜风味杯面", 69),
            _product("p_beauty_006", "巴黎欧莱雅防晒隔离露", 170),
        ])
        db.commit()

        node = purchase_help_node(db)
        node({"query": "把刚才推荐的都加入购物车", "memory": {"last_product_ids": ["p_food_020", "p_beauty_006"]}, "trace": []})
        result = node({"query": "刚才第二个不要了", "memory": {}, "trace": []})

        assert "已从购物车删除" in result["answer"]
        assert [item["product"]["id"] for item in list_cart_items(db)] == ["p_food_020"]
    finally:
        db.close()


def _product(
    product_id: str,
    title: str,
    price: int,
    *,
    stock: int = 10,
    brand: str = "测试品牌",
    category: str = "服饰运动",
) -> Product:
    return Product(
        id=product_id,
        title=title,
        category=category,
        brand=brand,
        price=price,
        description=title,
        rating=4.6,
        sales=1000,
        stock=stock,
        image_url="",
    )
