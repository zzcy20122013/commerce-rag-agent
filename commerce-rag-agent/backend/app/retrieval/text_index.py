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

    def search_products(self, query: str, *, limit: int = 5) -> list[dict[str, Any]]:
        return self._query(self.product_collection, query, limit)

    def search_faq(self, query: str, *, limit: int = 3) -> list[dict[str, Any]]:
        return self._query(self.faq_collection, query, limit)

    def _upsert(self, collection: Any, ids: list[str], documents: list[str], metadatas: list[dict[str, Any]]) -> None:
        collection.upsert(
            ids=ids,
            documents=documents,
            metadatas=metadatas,
            embeddings=self.embedding.embed_documents(documents),
        )

    def _query(self, collection: Any, query: str, limit: int) -> list[dict[str, Any]]:
        result = collection.query(
            query_embeddings=[self.embedding.embed_query(query)],
            n_results=limit,
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
    return (
        f"{product.title}\n"
        f"品类：{product.category}\n"
        f"品牌：{product.brand}\n"
        f"价格：{product.price}\n"
        f"描述：{product.description}\n"
        f"参数：{product.specs_json}"
    )
