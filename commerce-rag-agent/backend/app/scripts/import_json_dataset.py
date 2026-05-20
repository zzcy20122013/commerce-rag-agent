from pathlib import Path

from app.models.db import SessionLocal, init_db
from app.services.json_dataset_import_service import import_json_product_dataset


DEFAULT_DATASET_ROOT = Path("app/data/imports/ecommerce_agent_dataset")


def main() -> None:
    init_db()
    with SessionLocal() as db:
        result = import_json_product_dataset(db, DEFAULT_DATASET_ROOT)
    print(result)


if __name__ == "__main__":
    main()
