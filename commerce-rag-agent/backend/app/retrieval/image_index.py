import os
from typing import Any

import chromadb
from chromadb.config import Settings
from sqlalchemy.orm import Session

from app.embeddings.chinese_clip import ChineseClipEmbedding
from app.models.tables import Product, ProductImage


class ImageIndex:
    def __init__(
        self,
        *,
        chroma_path: str | None = None,
        embedding: ChineseClipEmbedding | None = None,
    ) -> None:
        self.chroma_path = chroma_path or os.getenv("CHROMA_PATH", "./app/data/chroma")
        self.embedding = embedding or ChineseClipEmbedding()
        self.client = chromadb.PersistentClient(
            path=self.chroma_path,
            settings=Settings(anonymized_telemetry=False),
        )
        self.collection = self.client.get_or_create_collection("product_images")

    def index_product_images(self, db: Session) -> None:
        rows = (
            db.query(ProductImage, Product)
            .join(Product, Product.id == ProductImage.product_id)
            .all()
        )
        if not rows:
            return
        ids = [f"{product.id}:{image.id}" for image, product in rows]
        documents = [f"{product.title} {product.category} {product.brand}" for image, product in rows]
        metadatas = [
            {
                "product_id": product.id,
                "image_id": image.id,
                "image_url": image.image_url,
                "local_path": image.local_path,
                "category": product.category,
                "brand": product.brand,
                "price": product.price,
                "rating": product.rating,
                "sales": product.sales,
                "stock": product.stock,
            }
            for image, product in rows
        ]
        embeddings = [self.embedding.embed_image(image.local_path) for image, product in rows]
        self.collection.upsert(ids=ids, documents=documents, metadatas=metadatas, embeddings=embeddings)

    def rebuild_product_images(self, db: Session) -> None:
        try:
            self.client.delete_collection("product_images")
        except Exception:
            pass
        self.collection = self.client.get_or_create_collection("product_images")
        self.index_product_images(db)

    def search_by_image(self, image_path: str, *, limit: int = 8) -> list[dict[str, Any]]:
        result = self.collection.query(
            query_embeddings=[self.embedding.embed_image(image_path)],
            n_results=limit,
            include=["documents", "metadatas", "distances"],
        )
        return [
            {
                "id": result["ids"][0][index],
                "text": result["documents"][0][index],
                "metadata": result["metadatas"][0][index],
                "distance": result["distances"][0][index],
                "image_similarity": max(0.0, 1.0 - result["distances"][0][index]),
            }
            for index in range(len(result["ids"][0]))
        ]
