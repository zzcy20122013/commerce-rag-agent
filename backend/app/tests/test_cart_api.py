from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.cart import get_db, router as cart_router
from app.models.db import Base
from app.models.tables import Product


def test_cart_api_add_list_update_and_remove(monkeypatch) -> None:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSession = sessionmaker(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = TestingSession()
    db.add(_product("p_pants_001", "通勤直筒长裤", 199))
    db.commit()
    db.close()

    def override_get_db():
        request_db = TestingSession()
        try:
            yield request_db
        finally:
            request_db.close()

    monkeypatch.setattr("app.api.cart.init_db", lambda: None)
    app = FastAPI()
    app.include_router(cart_router)
    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)

    assert client.post("/api/cart/items", json={"product_id": "p_pants_001", "quantity": 2}).status_code == 200
    listed = client.get("/api/cart").json()
    assert listed["items"][0]["quantity"] == 2

    assert client.put("/api/cart/items/1", json={"quantity": 3}).status_code == 200
    assert client.get("/api/cart").json()["items"][0]["quantity"] == 3

    assert client.delete("/api/cart/items/1").status_code == 200
    assert client.get("/api/cart").json()["items"] == []


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
