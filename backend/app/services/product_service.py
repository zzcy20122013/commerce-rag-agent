import json
import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.tables import Document, Product, ProductTag
from app.services.taxonomy import product_matches_subcategory


PRODUCT_ID_PATTERN = re.compile(r"\bp(?:_\w+)?_\d{3}\b|\bp\d{3}\b", re.IGNORECASE)


def filter_products(
    db: Session,
    *,
    category: str | None = None,
    subcategory: str | None = None,
    budget_max: int | None = None,
    in_stock_only: bool = True,
) -> list[Product]:
    statement = select(Product)
    if category:
        statement = statement.where(Product.category == category)
    if budget_max is not None:
        statement = statement.where(Product.price <= budget_max)
    if in_stock_only:
        statement = statement.where(Product.stock > 0)
    statement = statement.order_by(Product.rating.desc(), Product.sales.desc())
    products = list(db.scalars(statement).all())
    if subcategory:
        products = [product for product in products if product_matches_subcategory(product, subcategory)]
    return products


def get_products_by_ids(db: Session, product_ids: list[str]) -> list[Product]:
    if not product_ids:
        return []
    products = list(db.scalars(select(Product).where(Product.id.in_(product_ids))).all())
    product_by_id = {product.id: product for product in products}
    return [product_by_id[product_id] for product_id in product_ids if product_id in product_by_id]


def find_products_by_query(db: Session, query: str, *, limit: int = 5) -> list[Product]:
    lowered = query.lower()
    explicit_ids = [match.lower() for match in PRODUCT_ID_PATTERN.findall(lowered)]
    if explicit_ids:
        found = get_products_by_ids(db, explicit_ids)
        if found:
            return found[:limit]

    products = list(db.scalars(select(Product).where(Product.stock > 0)).all())
    scored = []
    for product in products:
        haystack = " ".join([product.id, product.title, product.category, product.brand, product.description]).lower()
        score = sum(1 for char in set(lowered) if char.strip() and char in haystack)
        if product.id.lower() in lowered:
            score += 50
        if product.title.lower() in lowered:
            score += 30
        if product.category.lower() in lowered:
            score += 10
        if score:
            scored.append((score, product))
    return [product for _, product in sorted(scored, key=lambda item: item[0], reverse=True)[:limit]]


def get_product_tags(db: Session, product_id: str) -> list[ProductTag]:
    return list(db.scalars(select(ProductTag).where(ProductTag.product_id == product_id)).all())


def get_product_knowledge_docs(db: Session, product_id: str, *, limit: int = 4) -> list[dict]:
    rows = list(
        db.scalars(
            select(Document)
            .where(Document.doc_type == "product_knowledge")
            .where(Document.source_file.like(f"{product_id}:%"))
            .order_by(Document.source_file.asc())
        ).all()
    )
    docs = []
    for row in rows[:limit]:
        try:
            metadata = json.loads(row.metadata_json or "{}")
        except json.JSONDecodeError:
            metadata = {}
        docs.append(
            {
                "id": row.id,
                "source_file": row.source_file,
                "text": metadata.get("text", ""),
                "metadata": metadata,
            }
        )
    return docs
