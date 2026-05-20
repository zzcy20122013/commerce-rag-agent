from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.models.db import get_db, init_db
from app.models.tables import Product
from app.scripts.seed_products import seed_product_images, seed_products


router = APIRouter(prefix="/api/products", tags=["products"])


@router.get("/{product_id}")
def get_product(product_id: str, db: Session = Depends(get_db)) -> dict:
    init_db()
    seed_products(db)
    seed_product_images(db)
    product = db.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return {
        "id": product.id,
        "title": product.title,
        "category": product.category,
        "brand": product.brand,
        "price": product.price,
        "description": product.description,
        "specs_json": product.specs_json,
        "rating": product.rating,
        "sales": product.sales,
        "stock": product.stock,
        "image_url": product.image_url,
    }
