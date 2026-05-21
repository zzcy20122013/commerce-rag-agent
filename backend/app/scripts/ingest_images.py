from app.models.db import SessionLocal, init_db
from app.retrieval.image_index import ImageIndex


def main() -> None:
    init_db()
    with SessionLocal() as db:
        ImageIndex().index_product_images(db)


if __name__ == "__main__":
    main()
