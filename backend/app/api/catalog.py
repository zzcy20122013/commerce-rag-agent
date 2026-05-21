from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.orm import Session

from app.models.db import get_db, init_db
from app.services.catalog_import_service import IMPORT_DIR, import_catalog_csv
from app.services.index_job_service import rebuild_all_indexes


router = APIRouter(prefix="/api/catalog", tags=["catalog"])


@router.post("/import")
async def import_catalog(
    file: UploadFile = File(...),
    image_root: str = Form(""),
    db: Session = Depends(get_db),
) -> dict:
    init_db()
    IMPORT_DIR.mkdir(parents=True, exist_ok=True)
    target = IMPORT_DIR / (file.filename or "catalog.csv")
    target.write_bytes(await file.read())
    return import_catalog_csv(
        db,
        target,
        image_root=Path(image_root) if image_root else target.parent,
    )


@router.post("/reindex")
def reindex_catalog(db: Session = Depends(get_db)) -> dict:
    init_db()
    return rebuild_all_indexes(db)
