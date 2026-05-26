from fastapi import APIRouter, File, HTTPException, UploadFile

from app.services.image_service import resolve_upload_path, save_upload_image
from app.services.vlm_service import VisionLanguageService, build_visual_confirmation_prompt


router = APIRouter(prefix="/api/upload", tags=["upload"])


@router.post("/image")
def upload_image(file: UploadFile = File(...)) -> dict[str, str]:
    try:
        return save_upload_image(file)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/image/{upload_id}/intent")
def recognize_image_intent(upload_id: str) -> dict:
    image_path = resolve_upload_path(upload_id)
    if not image_path:
        raise HTTPException(status_code=404, detail="Upload image not found")
    result = VisionLanguageService().analyze_image(image_path, query="请生成用户确认后可发送的拍照找货需求")
    return {
        "upload_id": upload_id,
        "prompt": build_visual_confirmation_prompt(result),
        "vlm_enabled": result.enabled,
        "vlm_error": result.error,
        "attributes": result.attributes.to_dict(),
    }
