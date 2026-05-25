import os
from collections.abc import Generator
from pathlib import Path
from urllib.parse import urlparse

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


class Base(DeclarativeBase):
    pass


DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./app/data/commerce.db")

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def init_db() -> None:
    if DATABASE_URL.startswith("sqlite:///"):
        db_path = Path(urlparse(DATABASE_URL).path.lstrip("/"))
        db_path.parent.mkdir(parents=True, exist_ok=True)
    Base.metadata.create_all(bind=engine)
    _ensure_sqlite_order_address_columns()


def _ensure_sqlite_order_address_columns() -> None:
    if not DATABASE_URL.startswith("sqlite"):
        return
    inspector = inspect(engine)
    if not inspector.has_table("orders"):
        return
    existing_columns = {column["name"] for column in inspector.get_columns("orders")}
    required_columns = {
        "shipping_recipient_name": "VARCHAR(100) DEFAULT ''",
        "shipping_phone": "VARCHAR(40) DEFAULT ''",
        "shipping_address": "VARCHAR(300) DEFAULT ''",
    }
    missing_columns = [
        (name, ddl_type)
        for name, ddl_type in required_columns.items()
        if name not in existing_columns
    ]
    if not missing_columns:
        return
    with engine.begin() as connection:
        for name, ddl_type in missing_columns:
            connection.execute(text(f"ALTER TABLE orders ADD COLUMN {name} {ddl_type}"))


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
