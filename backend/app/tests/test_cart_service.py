from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.db import Base
from app.models.tables import Order, OrderItem, Product
from app.services.cart_service import (
    add_cart_item,
    checkout_cart,
    InsufficientStockError,
    list_cart_items,
    remove_cart_item_by_position,
    update_cart_item_quantity_by_position,
)
from app.services.product_service import filter_products


def test_cart_add_update_remove_by_position() -> None:
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    TestingSession = sessionmaker(bind=engine)
    Base.metadata.create_all(bind=engine)

    db = TestingSession()
    try:
        db.add(_product("p_pants_001", "通勤直筒长裤", 199))
        db.commit()

        add_cart_item(db, product_id="p_pants_001", quantity=1)
        add_cart_item(db, product_id="p_pants_001", quantity=2)

        items = list_cart_items(db)
        assert len(items) == 1
        assert items[0]["quantity"] == 3
        assert items[0]["product"]["title"] == "通勤直筒长裤"

        updated = update_cart_item_quantity_by_position(db, position=1, quantity=5)
        assert updated is not None
        assert list_cart_items(db)[0]["quantity"] == 5

        removed = remove_cart_item_by_position(db, position=1)
        assert removed is not None
        assert list_cart_items(db) == []
    finally:
        db.close()


def test_checkout_cart_deducts_stock_creates_orders_and_clears_cart() -> None:
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    TestingSession = sessionmaker(bind=engine)
    Base.metadata.create_all(bind=engine)

    db = TestingSession()
    try:
        db.add(_product("p_pants_001", "通勤直筒长裤", 199, stock=2))
        db.add(_product("p_pants_002", "通勤九分裤", 159, stock=1))
        db.commit()

        add_cart_item(db, product_id="p_pants_001", quantity=2)
        add_cart_item(db, product_id="p_pants_002", quantity=1)

        result = checkout_cart(db, shipping_address=_shipping_address())

        assert result["total"] == 199 * 2 + 159
        assert result["cart"]["items"] == []
        assert len(result["order_ids"]) == 1
        assert result["orders"][0]["status"] == "待支付"
        assert result["orders"][0]["shipping_address"] == _shipping_address()
        assert len(result["orders"][0]["items"]) == 2
        assert db.get(Product, "p_pants_001").stock == 0
        assert db.get(Product, "p_pants_002").stock == 0
        assert len(db.query(Order).all()) == 1
        assert len(db.query(OrderItem).all()) == 2
        assert filter_products(db, category="服饰运动") == []
    finally:
        db.close()


def test_checkout_cart_rejects_insufficient_stock_without_partial_deduction() -> None:
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    TestingSession = sessionmaker(bind=engine)
    Base.metadata.create_all(bind=engine)

    db = TestingSession()
    try:
        db.add(_product("p_pants_001", "通勤直筒长裤", 199, stock=1))
        db.commit()
        add_cart_item(db, product_id="p_pants_001", quantity=1)
        product = db.get(Product, "p_pants_001")
        product.stock = 0
        db.commit()

        try:
            checkout_cart(db, shipping_address=_shipping_address())
            raise AssertionError("checkout should reject insufficient stock")
        except InsufficientStockError as error:
            assert error.product_id == "p_pants_001"

        assert db.get(Product, "p_pants_001").stock == 0
        assert list_cart_items(db)[0]["quantity"] == 1
        assert db.query(Order).all() == []
    finally:
        db.close()


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


def _shipping_address() -> dict:
    return {
        "recipient_name": "张三",
        "phone": "13800000000",
        "address": "上海市浦东新区世纪大道 100 号 8 楼",
    }
