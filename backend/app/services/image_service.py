import os
import shutil
import time
import uuid
from pathlib import Path

from fastapi import UploadFile
from PIL import Image, UnidentifiedImageError


DATA_DIR = Path("app/data")
UPLOAD_DIR = DATA_DIR / "uploads"
PRODUCT_IMAGE_DIR = DATA_DIR / "product_images"
ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
ALLOWED_IMAGE_MIME_TYPES = {"image/jpeg", "image/png", "image/webp"}
IMAGE_FORMAT_TO_EXTENSION = {"JPEG": ".jpg", "PNG": ".png", "WEBP": ".webp"}
MAX_IMAGE_SIZE = 8 * 1024 * 1024


def ensure_image_dirs() -> None:
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    PRODUCT_IMAGE_DIR.mkdir(parents=True, exist_ok=True)


def save_upload_image(file: UploadFile) -> dict[str, str]:
    ensure_image_dirs()
    cleanup_old_uploads()
    extension = Path(file.filename or "").suffix.lower()
    if extension not in ALLOWED_IMAGE_EXTENSIONS:
        raise ValueError("Only jpg, jpeg, png and webp images are supported")
    content_type = (file.content_type or "").split(";", 1)[0].strip().lower()
    if content_type and content_type not in ALLOWED_IMAGE_MIME_TYPES:
        raise ValueError("Uploaded file MIME type is not an allowed image type")

    upload_id = f"upload_{uuid.uuid4().hex[:12]}"
    temp_target = UPLOAD_DIR / f"{upload_id}.tmp"
    size = 0
    with temp_target.open("wb") as output:
        while chunk := file.file.read(1024 * 1024):
            size += len(chunk)
            if size > MAX_IMAGE_SIZE:
                temp_target.unlink(missing_ok=True)
                raise ValueError("Image size must be <= 8MB")
            output.write(chunk)

    try:
        actual_format = _validate_image_file(temp_target)
    except ValueError:
        temp_target.unlink(missing_ok=True)
        raise
    actual_extension = IMAGE_FORMAT_TO_EXTENSION.get(actual_format)
    if actual_extension is None:
        temp_target.unlink(missing_ok=True)
        raise ValueError("Only jpg, jpeg, png and webp images are supported")
    allowed_declared_extensions = {actual_extension}
    if actual_extension == ".jpg":
        allowed_declared_extensions.add(".jpeg")
    if extension not in allowed_declared_extensions:
        temp_target.unlink(missing_ok=True)
        raise ValueError("Image extension does not match decoded image format")

    target = UPLOAD_DIR / f"{upload_id}{actual_extension}"
    temp_target.replace(target)
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
    actual_format = _validate_image_file(source)
    extension = IMAGE_FORMAT_TO_EXTENSION.get(actual_format, extension)
    resolved_image_id = image_id or f"img_{product_id}_{uuid.uuid4().hex[:8]}"
    target = PRODUCT_IMAGE_DIR / f"{resolved_image_id}{extension}"
    shutil.copyfile(source, target)
    return {
        "image_id": resolved_image_id,
        "product_id": product_id,
        "local_path": str(target),
        "image_url": f"/static/product_images/{target.name}",
    }


def cleanup_old_uploads(*, max_age_seconds: int | None = None) -> int:
    ensure_image_dirs()
    ttl = max_age_seconds if max_age_seconds is not None else _upload_ttl_seconds()
    if ttl <= 0:
        return 0
    cutoff = time.time() - ttl
    deleted = 0
    for path in UPLOAD_DIR.iterdir():
        if not path.is_file():
            continue
        if path.suffix.lower() not in ALLOWED_IMAGE_EXTENSIONS | {".tmp"}:
            continue
        try:
            if path.stat().st_mtime < cutoff:
                path.unlink(missing_ok=True)
                deleted += 1
        except OSError:
            continue
    return deleted


def _validate_image_file(path: Path) -> str:
    Image.MAX_IMAGE_PIXELS = _max_image_pixels()
    try:
        with Image.open(path) as image:
            image.verify()
            image_format = str(image.format or "").upper()
        with Image.open(path) as image:
            width, height = image.size
            if width <= 0 or height <= 0:
                raise ValueError("Image dimensions are invalid")
            if width * height > _max_image_pixels():
                raise ValueError("Image pixel count is too large")
            return image_format
    except (UnidentifiedImageError, OSError) as error:
        raise ValueError("Uploaded file is not a decodable image") from error


def _upload_ttl_seconds() -> int:
    try:
        hours = float(os.getenv("UPLOAD_RETENTION_HOURS", "24"))
    except ValueError:
        hours = 24
    return max(int(hours * 3600), 0)


def _max_image_pixels() -> int:
    try:
        return max(int(os.getenv("IMAGE_MAX_PIXELS", "25000000")), 1)
    except ValueError:
        return 25_000_000
