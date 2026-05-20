from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.orm import Session

from app.models.db import get_db
from app.services.document_service import ingest_document


router = APIRouter(prefix="/api/docs", tags=["docs"])


@router.post("/ingest")
async def ingest_doc(
    file: UploadFile = File(...),
    doc_type: str = Form("knowledge"),
    category: str = Form(""),
    version: str = Form("v1"),
    db: Session = Depends(get_db),
) -> dict:
    raw = await file.read()
    content = raw.decode("utf-8")
    return ingest_document(
        db,
        source_file=file.filename or "upload.txt",
        content=content,
        doc_type=doc_type,
        category=category,
        version=version,
    )
