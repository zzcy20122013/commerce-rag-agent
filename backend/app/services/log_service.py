import json
import uuid

from sqlalchemy.orm import Session

from app.models.tables import RecommendationLog, RetrievalLog


def log_retrieval(db: Session, *, session_id: str, query: str, intent: str, filters: dict, candidates: list) -> None:
    db.add(
        RetrievalLog(
            id=f"ret_{uuid.uuid4().hex[:12]}",
            session_id=session_id,
            query=query,
            intent=intent,
            filters_json=json.dumps(filters, ensure_ascii=False),
            candidates_json=json.dumps(candidates, ensure_ascii=False),
        )
    )
    db.commit()


def log_recommendation(db: Session, *, session_id: str, message_id: str, products: list) -> None:
    db.add(
        RecommendationLog(
            id=f"rec_{uuid.uuid4().hex[:12]}",
            session_id=session_id,
            message_id=message_id,
            products_json=json.dumps(products, ensure_ascii=False),
        )
    )
    db.commit()
