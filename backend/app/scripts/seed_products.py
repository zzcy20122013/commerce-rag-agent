import base64

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.db import SessionLocal, init_db
from app.models.tables import Product, ProductImage
from app.services.image_service import PRODUCT_IMAGE_DIR, ensure_image_dirs


PLACEHOLDER_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/p9sAAAAASUVORK5CYII="
)
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def seed_products(db: Session) -> None:
    """Legacy compatibility hook.

    Product data now comes from catalog CSV imports instead of embedded samples.
    """
    db.commit()


def seed_product_images(db: Session) -> None:
    ensure_image_dirs()
    products = db.scalars(select(Product)).all()
    for product in products:
        image_id = f"img_{product.id}_0"
        extension = ".png"
        local_path = PRODUCT_IMAGE_DIR / f"{image_id}{extension}"
        existing_image = db.get(ProductImage, image_id)
        if existing_image:
            product.image_url = existing_image.image_url
            continue
        if product.image_url and not product.image_url.endswith(f"{image_id}{extension}"):
            continue
        product.image_url = f"/static/product_images/{local_path.name}"
        if not _is_valid_placeholder_image(local_path):
            local_path.write_bytes(PLACEHOLDER_PNG)
        db.add(
            ProductImage(
                id=image_id,
                product_id=product.id,
                image_url=f"/static/product_images/{local_path.name}",
                local_path=str(local_path),
                is_primary=1,
            )
        )
    db.commit()


def _is_valid_placeholder_image(path) -> bool:
    if not path.exists():
        return False
    return path.read_bytes().startswith(PNG_SIGNATURE)


if __name__ == "__main__":
    init_db()
    with SessionLocal() as session:
        seed_products(session)
        seed_product_images(session)
