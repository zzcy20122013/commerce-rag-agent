import json
import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.models.tables import Document, IndexJob, Product, ProductImage, utc_now
from app.retrieval.document_index import DocumentIndex
from app.retrieval.image_index import ImageIndex
from app.retrieval.text_index import TextIndex


def rebuild_all_indexes(db: Session, *, chroma_path: str | None = None) -> dict[str, Any]:
    job = IndexJob(id=f"idx_{uuid.uuid4().hex[:12]}", status="running")
    db.add(job)
    db.commit()

    errors: list[dict[str, str]] = []
    product_text_count = 0
    knowledge_docs_count = 0
    product_images_count = 0
    try:
        product_text_count = rebuild_product_text_index(db, chroma_path=chroma_path)
        knowledge_docs_count = rebuild_knowledge_docs_index(db, chroma_path=chroma_path)
        product_images_count = rebuild_product_image_index(db, chroma_path=chroma_path)
        job.status = "completed"
    except Exception as error:  # pragma: no cover - persisted for operational diagnostics
        product_text_count = job.product_text_count
        knowledge_docs_count = job.knowledge_docs_count
        product_images_count = job.product_images_count
        job.status = "failed"
        errors.append({"error": str(error)})
        raise
    finally:
        job.product_text_count = product_text_count
        job.knowledge_docs_count = knowledge_docs_count
        job.product_images_count = product_images_count
        job.errors_json = json.dumps(errors, ensure_ascii=False)
        job.completed_at = utc_now()
        db.commit()

    return {
        "job_id": job.id,
        "status": job.status,
        "product_text_count": job.product_text_count,
        "knowledge_docs_count": job.knowledge_docs_count,
        "product_images_count": job.product_images_count,
    }


def rebuild_product_text_index(db: Session, *, chroma_path: str | None = None) -> int:
    index = TextIndex(chroma_path=chroma_path)
    index.rebuild_products(db)
    return db.query(Product).count()


def rebuild_knowledge_docs_index(db: Session, *, chroma_path: str | None = None) -> int:
    documents = db.query(Document).all()
    chunks = []
    for document in documents:
        metadata = safe_json(document.metadata_json)
        text = metadata.get("text") or metadata.get("content") or document_to_text(document, metadata)
        chunk_metadata = {
            key: value
            for key, value in metadata.items()
            if key != "text" and isinstance(value, str | int | float | bool)
        }
        chunks.append(
            {
                "id": f"rebuild_{document.id}_0",
                "text": text,
                "metadata": {
                    **chunk_metadata,
                    "document_id": document.id,
                    "source_file": document.source_file,
                    "doc_type": document.doc_type,
                    "category": document.category,
                    "version": document.version,
                    "chunk_index": 0,
                },
            }
        )
    DocumentIndex(chroma_path=chroma_path).rebuild_chunks(chunks)
    return len(chunks)


def rebuild_product_image_index(db: Session, *, chroma_path: str | None = None) -> int:
    ImageIndex(chroma_path=chroma_path).rebuild_product_images(db)
    return db.query(ProductImage).count()


def document_to_text(document: Document, metadata: dict[str, Any]) -> str:
    return (
        f"{document.source_file}\n"
        f"类型：{document.doc_type}\n"
        f"类目：{document.category}\n"
        f"版本：{document.version}\n"
        f"元数据：{json.dumps(metadata, ensure_ascii=False)}"
    )


def safe_json(value: str) -> dict[str, Any]:
    try:
        parsed = json.loads(value or "{}")
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}
