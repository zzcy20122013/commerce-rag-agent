from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.models.db import get_db, init_db
from app.services.order_service import (
    OrderNotFoundError,
    OrderStateError,
    cancel_order,
    complete_order,
    get_order_detail,
    list_orders,
    pay_order,
    refund_order,
    ship_order,
)


router = APIRouter(prefix="/api/orders", tags=["orders"])


class RefundRequest(BaseModel):
    reason: str = ""


@router.get("")
def get_orders(db: Session = Depends(get_db)) -> dict:
    init_db()
    return {"orders": list_orders(db)}


@router.get("/{order_id}")
def get_order(order_id: str, db: Session = Depends(get_db)) -> dict:
    init_db()
    order = get_order_detail(db, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order


@router.post("/{order_id}/pay")
def pay(order_id: str, db: Session = Depends(get_db)) -> dict:
    init_db()
    return _run_order_action(lambda: pay_order(db, order_id))


@router.post("/{order_id}/cancel")
def cancel(order_id: str, db: Session = Depends(get_db)) -> dict:
    init_db()
    return _run_order_action(lambda: cancel_order(db, order_id))


@router.post("/{order_id}/ship")
def ship(order_id: str, db: Session = Depends(get_db)) -> dict:
    init_db()
    return _run_order_action(lambda: ship_order(db, order_id))


@router.post("/{order_id}/complete")
def complete(order_id: str, db: Session = Depends(get_db)) -> dict:
    init_db()
    return _run_order_action(lambda: complete_order(db, order_id))


@router.post("/{order_id}/refund")
def refund(order_id: str, payload: RefundRequest, db: Session = Depends(get_db)) -> dict:
    init_db()
    return _run_order_action(lambda: refund_order(db, order_id, reason=payload.reason))


def _run_order_action(action):
    try:
        return action()
    except OrderNotFoundError as error:
        raise HTTPException(status_code=404, detail="Order not found") from error
    except OrderStateError as error:
        raise HTTPException(
            status_code=409,
            detail={"message": error.message, "order_id": error.order_id, "status": error.status},
        ) from error
