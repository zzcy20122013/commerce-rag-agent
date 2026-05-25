import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.tables import CartItem, Product, utc_now
from app.services.order_service import create_order_from_cart_rows


class CartServiceError(Exception):
    pass


class EmptyCartError(CartServiceError):
    pass


class ProductNotFoundError(CartServiceError):
    def __init__(self, product_id: str):
        super().__init__(f"Product not found: {product_id}")
        self.product_id = product_id


class InsufficientStockError(CartServiceError):
    def __init__(self, product_id: str, requested: int, available: int):
        super().__init__(f"Insufficient stock for {product_id}: requested {requested}, available {available}")
        self.product_id = product_id
        self.requested = requested
        self.available = available


def add_cart_item(db: Session, *, product_id: str, quantity: int = 1, user_id: str = "debug-user") -> CartItem:
    quantity = max(quantity, 1)
    product = db.get(Product, product_id)
    if not product:
        raise ProductNotFoundError(product_id)
    existing = db.scalar(
        select(CartItem)
        .where(CartItem.user_id == user_id)
        .where(CartItem.product_id == product_id)
    )
    if existing:
        requested = existing.quantity + quantity
        if requested > product.stock:
            raise InsufficientStockError(product_id, requested, product.stock)
        existing.quantity += quantity
        existing.updated_at = utc_now()
        db.commit()
        db.refresh(existing)
        return existing

    if quantity > product.stock:
        raise InsufficientStockError(product_id, quantity, product.stock)

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
    product = db.get(Product, item.product_id)
    if not product:
        raise ProductNotFoundError(item.product_id)
    if quantity > product.stock:
        raise InsufficientStockError(item.product_id, quantity, product.stock)
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


def clear_cart_items(db: Session, *, user_id: str = "debug-user") -> int:
    items = list(
        db.scalars(
            select(CartItem)
            .where(CartItem.user_id == user_id)
            .order_by(CartItem.created_at.asc())
        ).all()
    )
    for item in items:
        db.delete(item)
    db.commit()
    return len(items)


def checkout_cart(db: Session, *, user_id: str = "debug-user") -> dict:
    rows = list(
        db.execute(
            select(CartItem, Product)
            .join(Product, Product.id == CartItem.product_id)
            .where(CartItem.user_id == user_id)
            .order_by(CartItem.created_at.asc())
        ).all()
    )
    if not rows:
        raise EmptyCartError("Cart is empty")

    checkout_items = []
    for item, product in rows:
        if item.quantity > product.stock:
            raise InsufficientStockError(product.id, item.quantity, product.stock)
        checkout_items.append(_cart_item_payload(item, product))

    total = sum(row["subtotal"] for row in checkout_items)
    for item, product in rows:
        product.stock -= item.quantity
    order = create_order_from_cart_rows(db, rows, user_id=user_id)
    for item, _product in rows:
        db.delete(item)
    db.commit()

    refreshed_items = []
    for payload in checkout_items:
        product = db.get(Product, payload["product"]["id"])
        refreshed = dict(payload)
        refreshed["product"] = {**payload["product"], "stock": product.stock if product else 0}
        refreshed_items.append(refreshed)

    return {
        "order_ids": [order["id"]],
        "orders": [order],
        "items": refreshed_items,
        "total": total,
        "cart": {"items": [], "total": 0},
    }


def _cart_item_payload(item: CartItem, product: Product) -> dict:
    return {
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
