import re
import shutil
from pathlib import Path
from urllib.parse import urlparse

from app.services.image_service import PRODUCT_IMAGE_DIR, ensure_image_dirs


PLACEHOLDER_PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x04\x00\x00\x00\xb5\x1c\x0c\x02\x00\x00\x00\x0bIDATx\xdac\xfc\xff"
    b"\x1f\x00\x03\x03\x02\x00\xef\xbf\xa7\xdb\x00\x00\x00\x00IEND\xaeB`\x82"
)
ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


def prepare_product_image(
    *,
    product_id: str,
    image_file: str,
    image_root: Path | None = None,
    asset_dir: Path | None = None,
) -> dict[str, str]:
    ensure_image_dirs()
    target_dir = asset_dir or PRODUCT_IMAGE_DIR
    target_dir.mkdir(parents=True, exist_ok=True)

    if image_file.startswith(("http://", "https://")):
        return {
            "image_id": f"img_{product_id}_0",
            "image_url": image_file,
            "local_path": image_file,
        }

    source = resolve_image_source(image_file, image_root)
    if source and source.exists() and source.suffix.lower() in ALLOWED_IMAGE_EXTENSIONS:
        filename = stable_asset_name(product_id, source.name)
        target = target_dir / filename
        shutil.copyfile(source, target)
    else:
        target = target_dir / f"{sanitize(product_id)}_placeholder.png"
        if not target.exists() or not target.read_bytes().startswith(b"\x89PNG"):
            target.write_bytes(PLACEHOLDER_PNG)

    return {
        "image_id": f"img_{product_id}_0",
        "image_url": f"/static/product_images/{target.name}",
        "local_path": str(target),
    }


def resolve_image_source(image_file: str, image_root: Path | None) -> Path | None:
    if not image_file:
        return None
    parsed = urlparse(image_file)
    if parsed.scheme:
        return None
    source = Path(image_file)
    if not source.is_absolute() and image_root:
        source = image_root / source
    return source


def stable_asset_name(product_id: str, filename: str) -> str:
    source = Path(filename)
    extension = source.suffix.lower() if source.suffix.lower() in ALLOWED_IMAGE_EXTENSIONS else ".png"
    return f"{sanitize(product_id)}_{sanitize(source.stem)}{extension}"


def sanitize(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_-]+", "_", value.strip())
    return cleaned.strip("_") or "asset"
