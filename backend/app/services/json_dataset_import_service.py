import json
import uuid
from pathlib import Path
from typing import Any

from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.models.tables import (
    Document,
    ImportJob,
    Product,
    ProductAttribute,
    ProductImage,
    ProductSku,
    ProductTag,
    utc_now,
)
from app.services.product_asset_service import prepare_product_image


def import_json_product_dataset(
    db: Session,
    dataset_root: str | Path,
    *,
    asset_dir: str | Path | None = None,
) -> dict[str, Any]:
    root = Path(dataset_root)
    if not root.exists():
        raise FileNotFoundError(f"Dataset root not found: {root}")

    json_files = sorted(root.glob("*/data/*.json"))
    job = ImportJob(
        id=f"imp_{uuid.uuid4().hex[:12]}",
        source_file=str(root),
        status="running",
        total_rows=len(json_files),
    )
    db.add(job)
    db.commit()

    imported = 0
    errors: list[dict[str, Any]] = []
    for index, json_file in enumerate(json_files, start=1):
        try:
            payload = json.loads(json_file.read_text(encoding="utf-8"))
            upsert_dataset_product(db, payload, dataset_root=root, asset_dir=Path(asset_dir) if asset_dir else None)
            imported += 1
        except Exception as error:
            errors.append({"row": index, "source_file": str(json_file), "error": str(error)})

    job.imported_count = imported
    job.failed_count = len(errors)
    job.errors_json = json.dumps(errors, ensure_ascii=False)
    job.status = "completed" if not errors else "completed_with_errors"
    job.completed_at = utc_now()
    db.commit()
    return {
        "job_id": job.id,
        "source_file": str(root),
        "total_rows": len(json_files),
        "imported_count": imported,
        "failed_count": len(errors),
        "errors": errors,
    }


def upsert_dataset_product(
    db: Session,
    payload: dict[str, Any],
    *,
    dataset_root: Path,
    asset_dir: Path | None,
) -> None:
    product_id = required_text(payload, "product_id")
    category = required_text(payload, "category")
    sub_category = str(payload.get("sub_category") or "").strip()
    knowledge = payload.get("rag_knowledge") or {}
    skus = payload.get("skus") or []
    reviews = knowledge.get("user_reviews") or []
    base_price = int(round(float(payload.get("base_price") or min_sku_price(skus) or 0)))
    image = prepare_product_image(
        product_id=product_id,
        image_file=str(payload.get("image_path") or ""),
        image_root=dataset_root,
        asset_dir=asset_dir,
    )
    specs = {
        "sub_category": sub_category,
        "sku_count": len(skus),
        "price_range": price_range(skus, base_price),
        "faq_count": len(knowledge.get("official_faq") or []),
        "review_count": len(reviews),
    }
    db.merge(
        Product(
            id=product_id,
            title=required_text(payload, "title"),
            category=category,
            brand=required_text(payload, "brand"),
            price=base_price,
            description=str(knowledge.get("marketing_description") or payload.get("title") or "").strip(),
            specs_json=json.dumps(specs, ensure_ascii=False),
            rating=average_rating(reviews),
            sales=estimated_sales(reviews),
            stock=estimate_stock(skus),
            image_url=image["image_url"],
        )
    )
    db.merge(
        ProductImage(
            id=image["image_id"],
            product_id=product_id,
            image_url=image["image_url"],
            local_path=image["local_path"],
            is_primary=1,
        )
    )
    replace_skus(db, product_id, skus, image["image_url"])
    replace_attributes(db, product_id, category, sub_category, payload)
    replace_tags(db, product_id, category, sub_category, payload, knowledge)
    replace_documents(db, product_id, category, payload, knowledge)
    db.commit()


def replace_skus(db: Session, product_id: str, skus: list[dict[str, Any]], image_url: str) -> None:
    db.execute(delete(ProductSku).where(ProductSku.product_id == product_id))
    for index, sku in enumerate(skus):
        properties = sku.get("properties") or {}
        sku_name = " ".join(str(value) for value in properties.values()) or f"规格 {index + 1}"
        db.add(
            ProductSku(
                id=str(sku.get("sku_id") or f"sku_{product_id}_{index}"),
                product_id=product_id,
                sku_name=sku_name,
                specs_json=json.dumps(properties, ensure_ascii=False),
                price=int(round(float(sku.get("price") or 0))),
                stock=80,
                image_url=image_url,
            )
        )


def replace_attributes(
    db: Session,
    product_id: str,
    category: str,
    sub_category: str,
    payload: dict[str, Any],
) -> None:
    db.execute(delete(ProductAttribute).where(ProductAttribute.product_id == product_id))
    attributes = {
        "类目": category,
        "子类目": sub_category,
        "品牌": str(payload.get("brand") or ""),
    }
    for index, (name, value) in enumerate(attributes.items()):
        if value:
            db.add(ProductAttribute(id=f"attr_{product_id}_{index}", product_id=product_id, name=name, value=value))


def replace_tags(
    db: Session,
    product_id: str,
    category: str,
    sub_category: str,
    payload: dict[str, Any],
    knowledge: dict[str, Any],
) -> None:
    db.execute(delete(ProductTag).where(ProductTag.product_id == product_id))
    tags = [category, sub_category, str(payload.get("brand") or "")]
    tags.extend(extract_keywords(str(knowledge.get("marketing_description") or "")))
    for index, value in enumerate(dict.fromkeys(item for item in tags if item)):
        db.add(ProductTag(id=f"tag_{product_id}_{index}", product_id=product_id, tag_type="tag", value=value[:100]))


def replace_documents(
    db: Session,
    product_id: str,
    category: str,
    payload: dict[str, Any],
    knowledge: dict[str, Any],
) -> None:
    db.execute(delete(Document).where(Document.source_file.like(f"{product_id}:%")))
    chunks = build_knowledge_chunks(payload, knowledge)
    for index, text in enumerate(chunks):
        document_id = f"doc_{product_id}_{index}"
        db.add(
            Document(
                id=document_id,
                source_file=f"{product_id}:{index}",
                doc_type="product_knowledge",
                category=category,
                version="dataset_v1",
                metadata_json=json.dumps({"product_id": product_id, "text": text}, ensure_ascii=False),
            )
        )


def build_knowledge_chunks(payload: dict[str, Any], knowledge: dict[str, Any]) -> list[str]:
    product_id = str(payload.get("product_id") or "")
    title = str(payload.get("title") or "")
    chunks: list[str] = []
    description = str(knowledge.get("marketing_description") or "").strip()
    if description:
        chunks.append(f"{title}\n商品ID：{product_id}\n营销说明：{description}")
    for faq in knowledge.get("official_faq") or []:
        question = str(faq.get("question") or "").strip()
        answer = str(faq.get("answer") or "").strip()
        if question or answer:
            chunks.append(f"{title}\n商品ID：{product_id}\nFAQ：{question}\n回答：{answer}")
    reviews = knowledge.get("user_reviews") or []
    if reviews:
        review_lines = [
            f"{item.get('nickname', '用户')}（{item.get('rating', 0)}星）：{item.get('content', '')}"
            for item in reviews
        ]
        chunks.append(f"{title}\n商品ID：{product_id}\n用户评价：\n" + "\n".join(review_lines))
    return chunks


def required_text(payload: dict[str, Any], key: str) -> str:
    value = str(payload.get(key) or "").strip()
    if not value:
        raise ValueError(f"{key} is required")
    return value


def min_sku_price(skus: list[dict[str, Any]]) -> float:
    prices = [float(sku.get("price") or 0) for sku in skus if sku.get("price") is not None]
    return min(prices) if prices else 0


def price_range(skus: list[dict[str, Any]], fallback: int) -> dict[str, int]:
    prices = [int(round(float(sku.get("price") or 0))) for sku in skus if sku.get("price") is not None]
    if not prices:
        prices = [fallback]
    return {"min": min(prices), "max": max(prices)}


def average_rating(reviews: list[dict[str, Any]]) -> float:
    ratings = [float(item.get("rating") or 0) for item in reviews if item.get("rating") is not None]
    if not ratings:
        return 4.5
    return round(sum(ratings) / len(ratings), 1)


def estimated_sales(reviews: list[dict[str, Any]]) -> int:
    return max(100, len(reviews) * 350)


def estimate_stock(skus: list[dict[str, Any]]) -> int:
    return max(80, len(skus) * 80)


def extract_keywords(text: str) -> list[str]:
    candidates = [
        "敏感肌",
        "保湿",
        "修护",
        "抗初老",
        "通勤",
        "学生",
        "性价比",
        "送礼",
        "低脂",
        "运动",
        "降噪",
        "续航",
        "轻薄",
        "便携",
    ]
    return [keyword for keyword in candidates if keyword in text]
