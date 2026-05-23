from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.models.db import get_db, init_db
from app.models.tables import Product
from app.services.cart_service import (
    add_cart_item,
    list_cart_items,
    remove_cart_item_by_position,
    update_cart_item_quantity_by_position,
)


router = APIRouter(prefix="/api/cart", tags=["cart"])


class AddCartItemRequest(BaseModel):
    product_id: str
    quantity: int = 1


class UpdateCartItemRequest(BaseModel):
    quantity: int


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
    add_cart_item(db, product_id=payload.product_id, quantity=payload.quantity)
    items = list_cart_items(db)
    return {"items": items, "total": sum(item["subtotal"] for item in items)}


@router.put("/items/{position}")
def update_item(position: int, payload: UpdateCartItemRequest, db: Session = Depends(get_db)) -> dict:
    init_db()
    if payload.quantity < 1:
        raise HTTPException(status_code=400, detail="quantity must be >= 1")
    if not update_cart_item_quantity_by_position(db, position=position, quantity=payload.quantity):
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
