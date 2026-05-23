import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.tables import CartItem, Product, utc_now


def add_cart_item(db: Session, *, product_id: str, quantity: int = 1, user_id: str = "debug-user") -> CartItem:
    quantity = max(quantity, 1)
    existing = db.scalar(
        select(CartItem)
        .where(CartItem.user_id == user_id)
        .where(CartItem.product_id == product_id)
    )
    if existing:
        existing.quantity += quantity
        existing.updated_at = utc_now()
        db.commit()
        db.refresh(existing)
        return existing

    item = CartItem(
        id=f"cart_{uuid.uuid4().hex[:12]}",
        user_id=user_id,
        product_id=product_id,
        quantity=quantity,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def list_cart_items(db: Session, *, user_id: str = "debug-user") -> list[dict]:
    rows = list(
        db.execute(
            select(CartItem, Product)
            .join(Product, Product.id == CartItem.product_id)
            .where(CartItem.user_id == user_id)
            .order_by(CartItem.created_at.asc())
        ).all()
    )
    return [
        {
            "id": item.id,
            "quantity": item.quantity,
            "product": {
                "id": product.id,
                "title": product.title,
                "price": product.price,
                "stock": product.stock,
                "image_url": product.image_url,
            },
            "subtotal": product.price * item.quantity,
        }
        for item, product in rows
    ]


def get_cart_item_by_position(db: Session, *, position: int, user_id: str = "debug-user") -> CartItem | None:
    items = list(
        db.scalars(
            select(CartItem)
            .where(CartItem.user_id == user_id)
            .order_by(CartItem.created_at.asc())
        ).all()
    )
    index = position - 1
    if index < 0 or index >= len(items):
        return None
    return items[index]


def update_cart_item_quantity_by_position(
    db: Session,
    *,
    position: int,
    quantity: int,
    user_id: str = "debug-user",
) -> CartItem | None:
    item = get_cart_item_by_position(db, position=position, user_id=user_id)
    if not item:
        return None
    item.quantity = max(quantity, 1)
    item.updated_at = utc_now()
    db.commit()
    db.refresh(item)
    return item


def remove_cart_item_by_position(db: Session, *, position: int, user_id: str = "debug-user") -> CartItem | None:
    item = get_cart_item_by_position(db, position=position, user_id=user_id)
    if not item:
        return None
    db.expunge(item)
    persisted = db.get(CartItem, item.id)
    if persisted:
        db.delete(persisted)
        db.commit()
    return item
