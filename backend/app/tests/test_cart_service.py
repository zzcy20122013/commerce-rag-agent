from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.db import Base
from app.models.tables import Product
from app.services.cart_service import (
    add_cart_item,
    list_cart_items,
    remove_cart_item_by_position,
    update_cart_item_quantity_by_position,
)


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
