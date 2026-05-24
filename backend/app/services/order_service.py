import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.tables import Order, OrderItem, Product


SAMPLE_ORDERS = [
    {
        "id": "ord_1001",
        "user_id": "debug-user",
        "product_id": "p201",
        "status": "已发货",
        "logistics_status": "包裹已到达本地分拣中心，预计明天送达。",
        "return_status": "未申请退货",
    },
    {
        "id": "ord_1002",
        "user_id": "debug-user",
        "product_id": "p209",
        "status": "已签收",
        "logistics_status": "订单已于昨天签收。",
        "return_status": "七天无理由退货期内，可提交退货申请。",
    },
]


def seed_orders(db: Session) -> None:
    existing_ids = set(db.scalars(select(Order.id)).all())
    for row in SAMPLE_ORDERS:
        if row["id"] not in existing_ids and db.get(Product, row["product_id"]):
            db.add(Order(**row))
    db.commit()


def find_order(db: Session, query: str, *, user_id: str = "debug-user") -> Order | None:
    normalized = query.lower()
    for token in normalized.replace(",", " ").split():
        if token.startswith("ord_"):
            order = db.get(Order, token)
            if order and order.user_id == user_id:
                return order
    return db.scalar(select(Order).where(Order.user_id == user_id).order_by(Order.created_at.desc()))


def create_order_from_cart_rows(db: Session, rows: list[tuple], *, user_id: str = "debug-user") -> dict:
    first_product = rows[0][1]
    order = Order(
        id=f"ord_{uuid.uuid4().hex[:12]}",
        user_id=user_id,
        product_id=first_product.id,
        status="待支付",
        logistics_status="订单已提交，库存已锁定，等待支付。",
        return_status="未申请售后",
    )
    db.add(order)
    db.flush()
    for cart_item, product in rows:
        db.add(
            OrderItem(
                id=f"order_item_{uuid.uuid4().hex[:12]}",
                order_id=order.id,
                product_id=product.id,
                title=product.title,
                image_url=product.image_url,
                quantity=cart_item.quantity,
                unit_price=product.price,
                subtotal=product.price * cart_item.quantity,
            )
        )
    return serialize_order(db, order)


def list_orders(db: Session, *, user_id: str = "debug-user") -> list[dict]:
    orders = list(
        db.scalars(
            select(Order)
            .where(Order.user_id == user_id)
            .order_by(Order.created_at.desc())
        ).all()
    )
    return [serialize_order(db, order) for order in orders]


def get_order_detail(db: Session, order_id: str, *, user_id: str = "debug-user") -> dict | None:
    order = db.get(Order, order_id)
    if not order or order.user_id != user_id:
        return None
    return serialize_order(db, order)


def pay_order(db: Session, order_id: str, *, user_id: str = "debug-user") -> dict:
    order = _require_order(db, order_id, user_id=user_id)
    if order.status == "待支付":
        order.status = "已支付"
        order.logistics_status = "支付成功，等待仓库出库。"
    db.commit()
    db.refresh(order)
    return serialize_order(db, order)


def cancel_order(db: Session, order_id: str, *, user_id: str = "debug-user") -> dict:
    order = _require_order(db, order_id, user_id=user_id)
    if order.status not in {"待支付"}:
        raise OrderStateError(order.id, order.status, "只有待支付订单可以取消")
    _restore_stock_for_order(db, order)
    order.status = "已取消"
    order.logistics_status = "订单已取消，锁定库存已释放。"
    order.return_status = "未进入售后"
    db.commit()
    db.refresh(order)
    return serialize_order(db, order)


def ship_order(db: Session, order_id: str, *, user_id: str = "debug-user") -> dict:
    order = _require_order(db, order_id, user_id=user_id)
    if order.status not in {"已支付", "已发货"}:
        raise OrderStateError(order.id, order.status, "只有已支付订单可以发货")
    order.status = "已发货"
    order.logistics_status = "包裹已出库，正在运输中。"
    db.commit()
    db.refresh(order)
    return serialize_order(db, order)


def complete_order(db: Session, order_id: str, *, user_id: str = "debug-user") -> dict:
    order = _require_order(db, order_id, user_id=user_id)
    if order.status not in {"已发货", "已完成"}:
        raise OrderStateError(order.id, order.status, "只有已发货订单可以确认收货")
    order.status = "已完成"
    order.logistics_status = "订单已确认收货。"
    db.commit()
    db.refresh(order)
    return serialize_order(db, order)


def refund_order(db: Session, order_id: str, *, reason: str = "", user_id: str = "debug-user") -> dict:
    order = _require_order(db, order_id, user_id=user_id)
    if order.status not in {"已支付", "已发货", "已完成"}:
        raise OrderStateError(order.id, order.status, "当前订单状态不能申请退款")
    _restore_stock_for_order(db, order)
    order.status = "已退款"
    order.return_status = f"退款已完成。原因：{reason.strip() or '用户申请售后'}。"
    order.logistics_status = "售后完成，库存已回补。"
    db.commit()
    db.refresh(order)
    return serialize_order(db, order)


def delete_order_record(db: Session, order_id: str, *, user_id: str = "debug-user") -> dict:
    order = _require_order(db, order_id, user_id=user_id)
    if order.status == "待支付":
        _restore_stock_for_order(db, order)
    for item in db.scalars(select(OrderItem).where(OrderItem.order_id == order.id)).all():
        db.delete(item)
    db.delete(order)
    db.commit()
    return {"ok": True, "deleted_order_id": order_id}


def serialize_order(db: Session, order: Order) -> dict:
    items = _order_items(db, order)
    total = sum(item["subtotal"] for item in items)
    return {
        "id": order.id,
        "status": order.status,
        "logistics_status": order.logistics_status,
        "return_status": order.return_status,
        "created_at": order.created_at.isoformat() if order.created_at else "",
        "items": items,
        "total": total,
    }


class OrderNotFoundError(Exception):
    pass


class OrderStateError(Exception):
    def __init__(self, order_id: str, status: str, message: str):
        super().__init__(message)
        self.order_id = order_id
        self.status = status
        self.message = message


def _require_order(db: Session, order_id: str, *, user_id: str) -> Order:
    order = db.get(Order, order_id)
    if not order or order.user_id != user_id:
        raise OrderNotFoundError(order_id)
    return order


def _order_items(db: Session, order: Order) -> list[dict]:
    rows = list(
        db.scalars(
            select(OrderItem)
            .where(OrderItem.order_id == order.id)
            .order_by(OrderItem.created_at.asc())
        ).all()
    )
    if not rows:
        product = db.get(Product, order.product_id)
        if not product:
            return []
        return [
            {
                "id": f"{order.id}_legacy_item",
                "quantity": 1,
                "subtotal": product.price,
                "product": _order_product_payload(product.id, product.title, product.price, product.stock, product.image_url),
            }
        ]
    return [
        {
            "id": item.id,
            "quantity": item.quantity,
            "subtotal": item.subtotal,
            "product": _order_product_payload(
                item.product_id,
                item.title,
                item.unit_price,
                db.get(Product, item.product_id).stock if db.get(Product, item.product_id) else 0,
                item.image_url,
            ),
        }
        for item in rows
    ]


def _restore_stock_for_order(db: Session, order: Order) -> None:
    if order.status in {"已取消", "已退款"}:
        return
    for item in db.scalars(select(OrderItem).where(OrderItem.order_id == order.id)).all():
        product = db.get(Product, item.product_id)
        if product:
            product.stock += item.quantity


def _order_product_payload(product_id: str, title: str, price: int, stock: int, image_url: str) -> dict:
    return {
        "id": product_id,
        "title": title,
        "price": price,
        "stock": stock,
        "image_url": image_url,
    }
