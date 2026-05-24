from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.cart import get_db as cart_get_db
from app.api.cart import router as cart_router
from app.api.orders import get_db as orders_get_db
from app.api.orders import router as orders_router
from app.models.db import Base
from app.models.tables import Product
from app.services.cart_service import add_cart_item, checkout_cart
from app.services.order_service import (
    complete_order,
    get_order_detail,
    list_orders,
    pay_order,
    refund_order,
    ship_order,
)


def test_checkout_creates_one_order_with_items_then_status_flow() -> None:
    db = _new_db()
    try:
        db.add(_product("p_pants_001", "通勤直筒长裤", 199, stock=3))
        db.add(_product("p_pants_002", "通勤九分裤", 159, stock=2))
        db.commit()

        add_cart_item(db, product_id="p_pants_001", quantity=2)
        add_cart_item(db, product_id="p_pants_002", quantity=1)

        result = checkout_cart(db)

        assert len(result["order_ids"]) == 1
        order_id = result["order_ids"][0]
        detail = get_order_detail(db, order_id)
        assert detail is not None
        assert detail["status"] == "待支付"
        assert detail["total"] == 557
        assert [item["quantity"] for item in detail["items"]] == [2, 1]
        assert db.get(Product, "p_pants_001").stock == 1
        assert db.get(Product, "p_pants_002").stock == 1

        assert pay_order(db, order_id)["status"] == "已支付"
        assert ship_order(db, order_id)["status"] == "已发货"
        assert complete_order(db, order_id)["status"] == "已完成"
        refunded = refund_order(db, order_id, reason="尺码不合适")
        assert refunded["status"] == "已退款"
        assert "尺码不合适" in refunded["return_status"]
        assert db.get(Product, "p_pants_001").stock == 3
        assert db.get(Product, "p_pants_002").stock == 2
    finally:
        db.close()


def test_orders_api_lists_and_updates_order_status(monkeypatch) -> None:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSession = sessionmaker(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = TestingSession()
    db.add(_product("p_pants_001", "通勤直筒长裤", 199, stock=2))
    db.commit()
    db.close()

    def override_get_db():
        request_db = TestingSession()
        try:
            yield request_db
        finally:
            request_db.close()

    monkeypatch.setattr("app.api.cart.init_db", lambda: None)
    monkeypatch.setattr("app.api.orders.init_db", lambda: None)
    app = FastAPI()
    app.include_router(cart_router)
    app.include_router(orders_router)
    app.dependency_overrides[cart_get_db] = override_get_db
    app.dependency_overrides[orders_get_db] = override_get_db
    client = TestClient(app)

    assert client.post("/api/cart/items", json={"product_id": "p_pants_001", "quantity": 1}).status_code == 200
    checked_out = client.post("/api/cart/checkout").json()
    order_id = checked_out["order_ids"][0]

    orders = client.get("/api/orders").json()
    assert orders["orders"][0]["id"] == order_id
    assert orders["orders"][0]["status"] == "待支付"

    paid = client.post(f"/api/orders/{order_id}/pay").json()
    assert paid["status"] == "已支付"

    refunded = client.post(f"/api/orders/{order_id}/refund", json={"reason": "不想要了"}).json()
    assert refunded["status"] == "已退款"
    assert "不想要了" in refunded["return_status"]


def _new_db() -> Session:
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    TestingSession = sessionmaker(bind=engine)
    Base.metadata.create_all(bind=engine)
    return TestingSession()


def _product(product_id: str, title: str, price: int, *, stock: int = 10) -> Product:
    return Product(
        id=product_id,
        title=title,
        category="服饰运动",
        brand="测试品牌",
        price=price,
        description=title,
        rating=4.6,
        sales=1000,
        stock=stock,
        image_url="",
    )
