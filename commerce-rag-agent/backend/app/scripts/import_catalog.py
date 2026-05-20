import argparse
from pathlib import Path

from app.models.db import SessionLocal, init_db
from app.services.catalog_import_service import import_catalog_csv


def main() -> None:
    parser = argparse.ArgumentParser(description="Import catalog CSV into SQLite product tables.")
    parser.add_argument("csv_path", help="Path to product catalog CSV.")
    parser.add_argument("--image-root", default="", help="Directory containing product image files.")
    args = parser.parse_args()

    init_db()
    with SessionLocal() as db:
        result = import_catalog_csv(
            db,
            Path(args.csv_path),
            image_root=Path(args.image_root) if args.image_root else Path(args.csv_path).parent,
        )
    print(result)


if __name__ == "__main__":
    main()
