from app.models.db import SessionLocal, init_db
from app.services.index_job_service import rebuild_all_indexes


def main() -> None:
    init_db()
    with SessionLocal() as db:
        result = rebuild_all_indexes(db)
    print(result)


if __name__ == "__main__":
    main()
