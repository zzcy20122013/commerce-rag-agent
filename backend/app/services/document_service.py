import csv
import io
import json
import uuid
from pathlib import Path

from sqlalchemy.orm import Session

from app.models.tables import Document
from app.retrieval.document_index import DocumentIndex


SUPPORTED_EXTENSIONS = {".md", ".txt", ".csv"}


def ingest_document(
    db: Session,
    *,
    source_file: str,
    content: str,
    doc_type: str = "knowledge",
    category: str = "",
    version: str = "v1",
    chroma_path: str | None = None,
) -> dict[str, int | str]:
    text = parse_document_text(source_file, content)
    document_id = f"doc_{uuid.uuid4().hex[:12]}"
    chunks = build_chunks(
        document_id=document_id,
        source_file=source_file,
        text=text,
        doc_type=doc_type,
        category=category,
        version=version,
    )
    DocumentIndex(chroma_path=chroma_path).add_chunks(chunks)
    db.add(
        Document(
            id=document_id,
            source_file=source_file,
            doc_type=doc_type,
            category=category,
            version=version,
            metadata_json=json.dumps({"chunks": len(chunks)}, ensure_ascii=False),
        )
    )
    db.commit()
    return {"document_id": document_id, "chunks": len(chunks)}


def parse_document_text(source_file: str, content: str) -> str:
    extension = Path(source_file).suffix.lower()
    if extension not in SUPPORTED_EXTENSIONS:
        raise ValueError(f"Unsupported document type: {extension}")
    if extension != ".csv":
        return content.strip()

    reader = csv.reader(io.StringIO(content))
    rows = [" | ".join(cell.strip() for cell in row if cell.strip()) for row in reader]
    return "\n".join(row for row in rows if row)


def build_chunks(
    *,
    document_id: str,
    source_file: str,
    text: str,
    doc_type: str,
    category: str,
    version: str,
    chunk_size: int = 500,
    overlap: int = 80,
) -> list[dict]:
    normalized = text.strip()
    if not normalized:
        return []
    chunks = []
    start = 0
    chunk_index = 0
    while start < len(normalized):
        end = min(start + chunk_size, len(normalized))
        chunk_text = normalized[start:end].strip()
        if chunk_text:
            chunks.append(
                {
                    "id": f"{document_id}_{chunk_index}",
                    "text": chunk_text,
                    "metadata": {
                        "document_id": document_id,
                        "source_file": source_file,
                        "doc_type": doc_type,
                        "category": category,
                        "version": version,
                        "chunk_index": chunk_index,
                    },
                }
            )
        if end == len(normalized):
            break
        start = max(end - overlap, start + 1)
        chunk_index += 1
    return chunks
