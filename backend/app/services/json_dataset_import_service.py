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
    knowledge_docs_count = 0
    errors: list[dict[str, Any]] = []
    for index, json_file in enumerate(json_files, start=1):
        try:
            payload = json.loads(json_file.read_text(encoding="utf-8"))
            knowledge_docs_count += upsert_dataset_product(
                db,
                payload,
                dataset_root=root,
                asset_dir=Path(asset_dir) if asset_dir else None,
            )
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
        "knowledge_docs_count": knowledge_docs_count,
        "failed_count": len(errors),
        "errors": errors,
    }


def upsert_dataset_product(
    db: Session,
    payload: dict[str, Any],
    *,
    dataset_root: Path,
    asset_dir: Path | None,
) -> int:
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
    specs = build_product_specs(
        sub_category=sub_category,
        skus=skus,
        base_price=base_price,
        knowledge=knowledge,
    )
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
    document_count = replace_documents(db, product_id, category, payload, knowledge)
    db.commit()
    return document_count


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
) -> int:
    db.execute(delete(Document).where(Document.source_file.like(f"{product_id}:%")))
    chunks = build_knowledge_chunks(payload, knowledge)
    for index, chunk in enumerate(chunks):
        document_id = f"doc_{product_id}_{chunk['metadata']['chunk_type']}_{index}"
        metadata = {
            **chunk["metadata"],
            "text": chunk["text"],
        }
        db.add(
            Document(
                id=document_id,
                source_file=f"{product_id}:{index}",
                doc_type="product_knowledge",
                category=category,
                version="dataset_v1",
                metadata_json=json.dumps(metadata, ensure_ascii=False),
            )
        )
    return len(chunks)


def build_knowledge_chunks(payload: dict[str, Any], knowledge: dict[str, Any]) -> list[dict[str, Any]]:
    product_id = str(payload.get("product_id") or "")
    title = str(payload.get("title") or "")
    skus = payload.get("skus") or []
    reviews = knowledge.get("user_reviews") or []
    base_metadata = {
        "product_id": product_id,
        "title": title,
        "brand": str(payload.get("brand") or ""),
        "category": str(payload.get("category") or ""),
        "sub_category": str(payload.get("sub_category") or ""),
    }
    chunks: list[dict[str, Any]] = []
    profile_parts = [
        f"{title}",
        f"商品ID：{product_id}",
        f"品牌：{base_metadata['brand']}",
        f"品类：{base_metadata['category']} / {base_metadata['sub_category']}",
    ]
    options = sku_options(skus)
    if options:
        profile_parts.append(f"规格选项：{'、'.join(options[:8])}")
    chunks.append(
        {
            "text": "\n".join(part for part in profile_parts if part),
            "metadata": {**base_metadata, "chunk_type": "product_profile", "sku_count": len(skus)},
        }
    )
    description = str(knowledge.get("marketing_description") or "").strip()
    if description:
        for section_index, section in enumerate(split_text_sections(description)):
            chunks.append(
                {
                    "text": f"{title}\n商品ID：{product_id}\n营销说明：{section}",
                    "metadata": {
                        **base_metadata,
                        "chunk_type": "marketing_description",
                        "section_index": section_index,
                    },
                }
            )
    for faq_index, faq in enumerate(knowledge.get("official_faq") or []):
        question = str(faq.get("question") or "").strip()
        answer = str(faq.get("answer") or "").strip()
        if question or answer:
            chunks.append(
                {
                    "text": f"{title}\n商品ID：{product_id}\nFAQ：{question}\n回答：{answer}",
                    "metadata": {
                        **base_metadata,
                        "chunk_type": "official_faq",
                        "question": question,
                        "faq_index": faq_index,
                    },
                }
            )
    if reviews:
        summary = review_summary(reviews)
        risk_text = "、".join(summary["risk_tags"]) if summary["risk_tags"] else "暂无明显集中差评风险"
        chunks.append(
            {
                "text": (
                    f"{title}\n商品ID：{product_id}\n评论摘要："
                    f"好评 {summary['positive_review_count']} 条，中评 {summary['neutral_review_count']} 条，"
                    f"差评 {summary['negative_review_count']} 条。"
                    f"正向关键词：{'、'.join(summary['positive_keywords']) or '暂无'}。"
                    f"风险提醒：{risk_text}。"
                ),
                "metadata": {
                    **base_metadata,
                    "chunk_type": "review_summary",
                    "positive_review_count": summary["positive_review_count"],
                    "neutral_review_count": summary["neutral_review_count"],
                    "negative_review_count": summary["negative_review_count"],
                    "risk_tags": "、".join(summary["risk_tags"]),
                },
            }
        )
    for review_index, item in enumerate(reviews):
        nickname = str(item.get("nickname") or "用户").strip()
        rating = int(item.get("rating") or 0)
        content = str(item.get("content") or "").strip()
        if content:
            sentiment = review_sentiment(rating)
            chunks.append(
                {
                    "text": f"{title}\n商品ID：{product_id}\n用户评价（{sentiment}）：{nickname}（{rating}星）：{content}",
                    "metadata": {
                        **base_metadata,
                        "chunk_type": "user_review",
                        "nickname": nickname,
                        "rating": rating,
                        "sentiment": sentiment,
                        "risk_keywords": "、".join(extract_negative_review_keywords([item])) if rating <= 2 else "",
                        "review_index": review_index,
                    },
                }
            )
    return chunks


def build_product_specs(
    *,
    sub_category: str,
    skus: list[dict[str, Any]],
    base_price: int,
    knowledge: dict[str, Any],
) -> dict[str, Any]:
    reviews = knowledge.get("user_reviews") or []
    return {
        "sub_category": sub_category,
        "sku_count": len(skus),
        "sku_options": sku_options(skus),
        "price_range": price_range(skus, base_price),
        "faq_count": len(knowledge.get("official_faq") or []),
        "review_count": len(reviews),
        "review_summary": review_summary(reviews),
    }


def sku_options(skus: list[dict[str, Any]]) -> list[str]:
    options = []
    for sku in skus:
        properties = sku.get("properties") or {}
        option = " ".join(str(value).strip() for value in properties.values() if str(value).strip())
        if option:
            options.append(option)
    return list(dict.fromkeys(options))


def review_summary(reviews: list[dict[str, Any]]) -> dict[str, Any]:
    negative_reviews = [review for review in reviews if int(review.get("rating") or 0) <= 2]
    neutral_reviews = [review for review in reviews if int(review.get("rating") or 0) == 3]
    positive_reviews = [review for review in reviews if int(review.get("rating") or 0) >= 4]
    negative_keywords = extract_negative_review_keywords(negative_reviews)
    return {
        "positive_review_count": len(positive_reviews),
        "neutral_review_count": len(neutral_reviews),
        "negative_review_count": len(negative_reviews),
        "positive_keywords": extract_positive_review_keywords(positive_reviews),
        "negative_keywords": negative_keywords,
        "risk_tags": negative_keywords[:5],
        "representative_negative_reviews": review_snippets(negative_reviews, limit=2),
    }


def extract_negative_review_keywords(reviews: list[dict[str, Any]]) -> list[str]:
    candidates = [
        "敏感肌",
        "刺痛",
        "泛红",
        "闷痘",
        "闭口",
        "拔干",
        "太干",
        "不适合",
        "浪费",
        "失望",
        "不好喝",
        "磨脚",
        "累脚",
        "压耳",
        "卡顿",
        "发热",
        "续航差",
    ]
    text = "\n".join(str(review.get("content") or "") for review in reviews)
    return [keyword for keyword in candidates if keyword in text]


def extract_positive_review_keywords(reviews: list[dict[str, Any]]) -> list[str]:
    candidates = [
        "温和",
        "保湿",
        "修护",
        "熬夜",
        "舒服",
        "轻薄",
        "便携",
        "续航",
        "降噪",
        "通勤",
        "好喝",
        "不磨脚",
        "性价比",
    ]
    text = "\n".join(str(review.get("content") or "") for review in reviews)
    return [keyword for keyword in candidates if keyword in text]


def review_snippets(reviews: list[dict[str, Any]], *, limit: int) -> list[str]:
    snippets = []
    for review in reviews:
        content = str(review.get("content") or "").strip()
        if content:
            snippets.append(content[:80])
    return snippets[:limit]


def review_sentiment(rating: int) -> str:
    if rating <= 2:
        return "negative"
    if rating == 3:
        return "neutral"
    return "positive"


def split_text_sections(text: str, *, max_length: int = 220) -> list[str]:
    cleaned = " ".join(text.split())
    if len(cleaned) <= max_length:
        return [cleaned]
    sections: list[str] = []
    current = ""
    for sentence in re_split_sentences(cleaned):
        if current and len(current) + len(sentence) > max_length:
            sections.append(current)
            current = sentence
        else:
            current = f"{current}{sentence}" if current else sentence
    if current:
        sections.append(current)
    return sections or [cleaned[:max_length]]


def re_split_sentences(text: str) -> list[str]:
    sentences: list[str] = []
    start = 0
    for index, char in enumerate(text):
        if char in "。！？!?；;":
            sentences.append(text[start : index + 1])
            start = index + 1
    if start < len(text):
        sentences.append(text[start:])
    return [sentence.strip() for sentence in sentences if sentence.strip()]


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
