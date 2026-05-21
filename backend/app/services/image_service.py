import shutil
import uuid
from pathlib import Path

from fastapi import UploadFile


DATA_DIR = Path("app/data")
UPLOAD_DIR = DATA_DIR / "uploads"
PRODUCT_IMAGE_DIR = DATA_DIR / "product_images"
ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
MAX_IMAGE_SIZE = 8 * 1024 * 1024


def ensure_image_dirs() -> None:
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    PRODUCT_IMAGE_DIR.mkdir(parents=True, exist_ok=True)


def save_upload_image(file: UploadFile) -> dict[str, str]:
    ensure_image_dirs()
    extension = Path(file.filename or "").suffix.lower()
    if extension not in ALLOWED_IMAGE_EXTENSIONS:
        raise ValueError("Only jpg, jpeg, png and webp images are supported")

    upload_id = f"upload_{uuid.uuid4().hex[:12]}"
    target = UPLOAD_DIR / f"{upload_id}{extension}"
    size = 0
    with target.open("wb") as output:
        while chunk := file.file.read(1024 * 1024):
            size += len(chunk)
            if size > MAX_IMAGE_SIZE:
                target.unlink(missing_ok=True)
                raise ValueError("Image size must be <= 8MB")
            output.write(chunk)

    return {
        "upload_id": upload_id,
        "local_path": str(target),
        "preview_url": f"/static/uploads/{target.name}",
    }


def resolve_upload_path(upload_id: str) -> str | None:
    ensure_image_dirs()
    for extension in ALLOWED_IMAGE_EXTENSIONS:
        candidate = UPLOAD_DIR / f"{upload_id}{extension}"
        if candidate.exists():
            return str(candidate)
    return None


def register_product_image_file(product_id: str, source_path: str, *, image_id: str | None = None) -> dict[str, str]:
    ensure_image_dirs()
    source = Path(source_path)
    extension = source.suffix.lower()
    if extension not in ALLOWED_IMAGE_EXTENSIONS:
        raise ValueError("Only jpg, jpeg, png and webp images are supported")
    resolved_image_id = image_id or f"img_{product_id}_{uuid.uuid4().hex[:8]}"
    target = PRODUCT_IMAGE_DIR / f"{resolved_image_id}{extension}"
    shutil.copyfile(source, target)
    return {
        "image_id": resolved_image_id,
        "product_id": product_id,
        "local_path": str(target),
        "image_url": f"/static/product_images/{target.name}",
    }
