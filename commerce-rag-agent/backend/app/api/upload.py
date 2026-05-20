from fastapi import APIRouter, File, HTTPException, UploadFile

from app.services.image_service import save_upload_image


router = APIRouter(prefix="/api/upload", tags=["upload"])


@router.post("/image")
def upload_image(file: UploadFile = File(...)) -> dict[str, str]:
    try:
        return save_upload_image(file)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
