from app.models.db import SessionLocal, init_db
from app.retrieval.text_index import TextIndex
from app.scripts.seed_products import seed_products


def main() -> None:
    init_db()
    index = TextIndex()
    with SessionLocal() as db:
        seed_products(db)
        index.index_products(db)
    index.index_faqs()


if __name__ == "__main__":
    main()
