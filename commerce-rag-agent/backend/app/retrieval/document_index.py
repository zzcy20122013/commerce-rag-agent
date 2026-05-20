import os
from typing import Any

import chromadb
from chromadb.config import Settings

from app.embeddings.bge_m3 import BgeM3Embedding


class DocumentIndex:
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
        self.collection = self.client.get_or_create_collection("knowledge_docs")

    def add_chunks(self, chunks: list[dict[str, Any]]) -> None:
        if not chunks:
            return
        documents = [chunk["text"] for chunk in chunks]
        self.collection.upsert(
            ids=[chunk["id"] for chunk in chunks],
            documents=documents,
            metadatas=[chunk["metadata"] for chunk in chunks],
            embeddings=self.embedding.embed_documents(documents),
        )

    def rebuild_chunks(self, chunks: list[dict[str, Any]]) -> None:
        try:
            self.client.delete_collection("knowledge_docs")
        except Exception:
            pass
        self.collection = self.client.get_or_create_collection("knowledge_docs")
        self.add_chunks(chunks)

    def search(self, query: str, *, limit: int = 5) -> list[dict[str, Any]]:
        result = self.collection.query(
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
