import json
import os
from typing import Any

import chromadb
from chromadb.config import Settings
from sqlalchemy.orm import Session

from app.embeddings.bge_m3 import BgeM3Embedding
from app.models.tables import Product


DEFAULT_FAQS = [
    {
        "id": "faq_return_policy",
        "text": "退货政策：签收后 7 天内，商品不影响二次销售可申请无理由退货；质量问题支持售后检测。",
        "metadata": {"topic": "退货政策"},
    },
    {
        "id": "faq_warranty",
        "text": "保修政策：电子产品按品牌官方保修规则执行，平台提供订单凭证和售后协助。",
        "metadata": {"topic": "保修政策"},
    },
    {
        "id": "faq_invoice",
        "text": "发票说明：下单后可在订单详情申请电子发票，抬头支持个人或企业。",
        "metadata": {"topic": "发票"},
    },
]


class TextIndex:
    def __init__(
        self,
        *,
        chroma_path: str | None = None,
        embedding: BgeM3Embedding | None = None,
    ) -> None:
        self.chroma_path = chroma_path or os.getenv("CHROMA_PATH", "./app/data/chroma")
        self.embedding = embedding or BgeM3Embedding()
        self.client = chromadb.PersistentClient(
            path=self.chroma_path,
            settings=Settings(anonymized_telemetry=False),
        )
        self.product_collection = self.client.get_or_create_collection("product_text")
        self.faq_collection = self.client.get_or_create_collection("faq")

    def index_products(self, db: Session) -> None:
        products = db.query(Product).all()
        if not products:
            return
        ids = [product.id for product in products]
        documents = [product_to_text(product) for product in products]
        metadatas = [
            {
                "product_id": product.id,
                "title": product.title,
                "category": product.category,
                "brand": product.brand,
                "price": product.price,
                "stock": product.stock,
            }
            for product in products
        ]
        self._upsert(self.product_collection, ids, documents, metadatas)

    def ensure_products_indexed(self, db: Session) -> None:
        try:
            if self.product_collection.count() > 0:
                return
        except Exception:
            pass
        self.index_products(db)

    def rebuild_products(self, db: Session) -> None:
        self._reset_collection("product_text")
        self.index_products(db)

    def index_faqs(self, faqs: list[dict[str, Any]] | None = None) -> None:
        rows = faqs or DEFAULT_FAQS
        self._upsert(
            self.faq_collection,
            [row["id"] for row in rows],
            [row["text"] for row in rows],
            [row["metadata"] for row in rows],
        )

    def rebuild_faqs(self, faqs: list[dict[str, Any]] | None = None) -> None:
        self._reset_collection("faq")
        self.index_faqs(faqs)

    def search_products(
        self,
        query: str,
        *,
        limit: int = 5,
        product_ids: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        return self._query(self.product_collection, query, limit, product_ids=product_ids)

    def search_faq(self, query: str, *, limit: int = 3) -> list[dict[str, Any]]:
        return self._query(self.faq_collection, query, limit)

    def _upsert(self, collection: Any, ids: list[str], documents: list[str], metadatas: list[dict[str, Any]]) -> None:
        collection.upsert(
            ids=ids,
            documents=documents,
            metadatas=metadatas,
            embeddings=self.embedding.embed_documents(documents),
        )

    def _query(
        self,
        collection: Any,
        query: str,
        limit: int,
        *,
        product_ids: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        where = None
        if product_ids:
            where = {"product_id": product_ids[0]} if len(product_ids) == 1 else {"product_id": {"$in": product_ids}}
        result = collection.query(
            query_embeddings=[self.embedding.embed_query(query)],
            n_results=limit,
            where=where,
            include=["documents", "metadatas", "distances"],
        )
        return [
            {
                "id": result["ids"][0][index],
                "text": result["documents"][0][index],
                "metadata": result["metadatas"][0][index],
                "distance": result["distances"][0][index],
            }
            for index in range(len(result["ids"][0]))
        ]

    def _reset_collection(self, name: str) -> None:
        try:
            self.client.delete_collection(name)
        except Exception:
            pass
        collection = self.client.get_or_create_collection(name)
        if name == "product_text":
            self.product_collection = collection
        if name == "faq":
            self.faq_collection = collection


def product_to_text(product: Product) -> str:
    specs = _safe_json(product.specs_json)
    parts = [
        product.title,
        f"品类：{product.category}",
        f"品牌：{product.brand}",
        f"价格：{product.price}",
        f"描述：{product.description}",
    ]
    sku_options = specs.get("sku_options") or []
    if sku_options:
        parts.append(f"规格选项：{'、'.join(str(option) for option in sku_options[:8])}")
    price_range = specs.get("price_range") or {}
    if price_range:
        parts.append(f"价格范围：{price_range.get('min')} 到 {price_range.get('max')} 元")
    review_summary = specs.get("review_summary") or {}
    if review_summary:
        parts.append(
            "评论摘要："
            f"好评 {review_summary.get('positive_review_count', 0)} 条，"
            f"中评 {review_summary.get('neutral_review_count', 0)} 条，"
            f"差评 {review_summary.get('negative_review_count', 0)} 条"
        )
        risk_tags = review_summary.get("risk_tags") or review_summary.get("negative_keywords") or []
        if risk_tags:
            parts.append(f"评论风险：{'、'.join(str(tag) for tag in risk_tags[:5])}")
        positive_keywords = review_summary.get("positive_keywords") or []
        if positive_keywords:
            parts.append(f"正向评价关键词：{'、'.join(str(keyword) for keyword in positive_keywords[:5])}")
    if specs.get("faq_count") is not None:
        parts.append(f"FAQ数量：{specs.get('faq_count')}")
    return "\n".join(part for part in parts if part)


def _safe_json(value: str) -> dict[str, Any]:
    try:
        parsed = json.loads(value or "{}")
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}
