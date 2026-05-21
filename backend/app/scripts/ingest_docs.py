import argparse
from pathlib import Path

from app.models.db import SessionLocal, init_db
from app.services.document_service import ingest_document


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("path")
    parser.add_argument("--doc-type", default="knowledge")
    parser.add_argument("--category", default="")
    parser.add_argument("--version", default="v1")
    args = parser.parse_args()

    path = Path(args.path)
    init_db()
    with SessionLocal() as db:
        result = ingest_document(
            db,
            source_file=path.name,
            content=path.read_text(encoding="utf-8"),
            doc_type=args.doc_type,
            category=args.category,
            version=args.version,
        )
    print(result)


if __name__ == "__main__":
    main()
