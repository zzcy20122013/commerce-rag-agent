from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.models.db import get_db, init_db
from app.models.tables import Product
from app.services.cart_service import (
    add_cart_item,
    checkout_cart,
    EmptyCartError,
    InsufficientStockError,
    list_cart_items,
    ProductNotFoundError,
    remove_cart_item_by_position,
    update_cart_item_quantity_by_position,
)
from app.services.order_service import ShippingAddressError


router = APIRouter(prefix="/api/cart", tags=["cart"])


class AddCartItemRequest(BaseModel):
    product_id: str
    quantity: int = 1


class UpdateCartItemRequest(BaseModel):
    quantity: int


class ShippingAddressRequest(BaseModel):
    recipient_name: str
    phone: str
    address: str


class CheckoutRequest(BaseModel):
    shipping_address: ShippingAddressRequest


@router.get("")
def get_cart(db: Session = Depends(get_db)) -> dict:
    init_db()
    items = list_cart_items(db)
    return {"items": items, "total": sum(item["subtotal"] for item in items)}


@router.post("/items")
def add_item(payload: AddCartItemRequest, db: Session = Depends(get_db)) -> dict:
    init_db()
    if payload.quantity < 1:
        raise HTTPException(status_code=400, detail="quantity must be >= 1")
    if not db.get(Product, payload.product_id):
        raise HTTPException(status_code=404, detail="Product not found")
    try:
        add_cart_item(db, product_id=payload.product_id, quantity=payload.quantity)
    except InsufficientStockError as error:
        raise HTTPException(
            status_code=409,
            detail={
                "message": "库存不足",
                "product_id": error.product_id,
                "requested": error.requested,
                "available": error.available,
            },
        ) from error
    items = list_cart_items(db)
    return {"items": items, "total": sum(item["subtotal"] for item in items)}


@router.put("/items/{position}")
def update_item(position: int, payload: UpdateCartItemRequest, db: Session = Depends(get_db)) -> dict:
    init_db()
    if payload.quantity < 1:
        raise HTTPException(status_code=400, detail="quantity must be >= 1")
    try:
        updated = update_cart_item_quantity_by_position(db, position=position, quantity=payload.quantity)
    except InsufficientStockError as error:
        raise HTTPException(
            status_code=409,
            detail={
                "message": "库存不足",
                "product_id": error.product_id,
                "requested": error.requested,
                "available": error.available,
            },
        ) from error
    except ProductNotFoundError as error:
        raise HTTPException(status_code=404, detail=f"Product not found: {error.product_id}") from error
    if not updated:
        raise HTTPException(status_code=404, detail="Cart item not found")
    items = list_cart_items(db)
    return {"items": items, "total": sum(item["subtotal"] for item in items)}


@router.delete("/items/{position}")
def remove_item(position: int, db: Session = Depends(get_db)) -> dict:
    init_db()
    if not remove_cart_item_by_position(db, position=position):
        raise HTTPException(status_code=404, detail="Cart item not found")
    items = list_cart_items(db)
    return {"items": items, "total": sum(item["subtotal"] for item in items)}


@router.post("/checkout")
def checkout(payload: CheckoutRequest, db: Session = Depends(get_db)) -> dict:
    init_db()
    try:
        return checkout_cart(db, shipping_address=payload.shipping_address.model_dump())
    except EmptyCartError as error:
        raise HTTPException(status_code=400, detail="购物车为空") from error
    except ShippingAddressError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except InsufficientStockError as error:
        raise HTTPException(
            status_code=409,
            detail={
                "message": "库存不足",
                "product_id": error.product_id,
                "requested": error.requested,
                "available": error.available,
            },
        ) from error
