from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.tables import Order, Product


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
