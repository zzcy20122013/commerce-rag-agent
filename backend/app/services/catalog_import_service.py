import csv
import json
import uuid
from pathlib import Path
from typing import Any

from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.models.tables import ImportJob, Product, ProductImage, ProductTag, utc_now
from app.services.product_asset_service import prepare_product_image


REQUIRED_FIELDS = ["id", "title", "category", "brand", "price", "description"]
CATALOG_DIR = Path("app/data/catalog")
IMPORT_DIR = Path("app/data/imports")


def import_catalog_csv(
    db: Session,
    csv_path: str | Path,
    *,
    image_root: str | Path | None = None,
    asset_dir: str | Path | None = None,
) -> dict[str, Any]:
    source = Path(csv_path)
    resolved_image_root = Path(image_root) if image_root else source.parent
    resolved_asset_dir = Path(asset_dir) if asset_dir else None
    job = ImportJob(
        id=f"imp_{uuid.uuid4().hex[:12]}",
        source_file=str(source),
        status="running",
    )
    db.add(job)
    db.commit()

    imported = 0
    errors: list[dict[str, Any]] = []
    rows = read_catalog_rows(source)
    job.total_rows = len(rows)

    for row_number, row in enumerate(rows, start=2):
        product_id = (row.get("id") or "").strip()
        try:
            normalized = normalize_catalog_row(row)
            upsert_product(
                db,
                normalized,
                image_root=resolved_image_root,
                asset_dir=resolved_asset_dir,
            )
            imported += 1
        except ValueError as error:
            errors.append({"row": row_number, "product_id": product_id or None, "error": str(error)})

    job.imported_count = imported
    job.failed_count = len(errors)
    job.errors_json = json.dumps(errors, ensure_ascii=False)
    job.status = "completed" if not errors else "completed_with_errors"
    job.completed_at = utc_now()
    db.commit()
    return {
        "job_id": job.id,
        "source_file": str(source),
        "imported_count": imported,
        "failed_count": len(errors),
        "errors": errors,
    }


def read_catalog_rows(csv_path: Path) -> list[dict[str, str]]:
    if not csv_path.exists():
        raise FileNotFoundError(f"Catalog file not found: {csv_path}")
    with csv_path.open("r", encoding="utf-8-sig", newline="") as input_file:
        return [dict(row) for row in csv.DictReader(input_file)]


def normalize_catalog_row(row: dict[str, str]) -> dict[str, Any]:
    for field in REQUIRED_FIELDS:
        if not (row.get(field) or "").strip():
            raise ValueError(f"{field} is required")
    return {
        "id": row["id"].strip(),
        "title": row["title"].strip(),
        "category": row["category"].strip(),
        "brand": row["brand"].strip(),
        "price": parse_int(row.get("price"), "price"),
        "description": row["description"].strip(),
        "specs_json": normalize_json(row.get("specs_json") or "{}"),
        "rating": parse_float(row.get("rating") or "0", "rating"),
        "sales": parse_int(row.get("sales") or "0", "sales"),
        "stock": parse_int(row.get("stock") or "0", "stock"),
        "tags": split_values(row.get("tags")),
        "audience": split_values(row.get("audience")),
        "use_cases": split_values(row.get("use_cases")),
        "selling_points": split_values(row.get("selling_points")),
        "image_file": (row.get("image_file") or "").strip(),
    }


def upsert_product(
    db: Session,
    row: dict[str, Any],
    *,
    image_root: Path,
    asset_dir: Path | None,
) -> None:
    image = prepare_product_image(
        product_id=row["id"],
        image_file=row["image_file"],
        image_root=image_root,
        asset_dir=asset_dir,
    )
    db.merge(
        Product(
            id=row["id"],
            title=row["title"],
            category=row["category"],
            brand=row["brand"],
            price=row["price"],
            description=row["description"],
            specs_json=row["specs_json"],
            rating=row["rating"],
            sales=row["sales"],
            stock=row["stock"],
            image_url=image["image_url"],
        )
    )
    db.merge(
        ProductImage(
            id=image["image_id"],
            product_id=row["id"],
            image_url=image["image_url"],
            local_path=image["local_path"],
            is_primary=1,
        )
    )
    db.execute(delete(ProductTag).where(ProductTag.product_id == row["id"]))
    add_tags(db, row["id"], "tag", row["tags"])
    add_tags(db, row["id"], "audience", row["audience"])
    add_tags(db, row["id"], "use_case", row["use_cases"])
    add_tags(db, row["id"], "selling_point", row["selling_points"])


def add_tags(db: Session, product_id: str, tag_type: str, values: list[str]) -> None:
    for index, value in enumerate(values):
        db.add(
            ProductTag(
                id=f"tag_{product_id}_{tag_type}_{index}",
                product_id=product_id,
                tag_type=tag_type,
                value=value,
            )
        )


def parse_int(value: str | None, field: str) -> int:
    try:
        return int(str(value or "").strip())
    except ValueError as error:
        raise ValueError(f"{field} must be an integer") from error


def parse_float(value: str | None, field: str) -> float:
    try:
        return float(str(value or "").strip())
    except ValueError as error:
        raise ValueError(f"{field} must be a number") from error


def normalize_json(value: str) -> str:
    try:
        return json.dumps(json.loads(value), ensure_ascii=False)
    except json.JSONDecodeError as error:
        raise ValueError("specs_json must be valid JSON") from error


def split_values(value: str | None) -> list[str]:
    raw = (value or "").replace(",", ";").replace("，", ";").replace("、", ";")
    return [item.strip() for item in raw.split(";") if item.strip()]
