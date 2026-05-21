from collections import Counter
from pathlib import Path
from typing import Any

from sqlalchemy import select

from app.evaluation.report import write_csv, write_markdown_report
from app.evaluation.runner import DEFAULT_REPORT_DIR
from app.models.db import SessionLocal
from app.models.tables import Feedback, Message, RecommendationLog


def export_negative_feedback(report_dir: str | Path = DEFAULT_REPORT_DIR) -> list[dict[str, Any]]:
    output_dir = Path(report_dir)
    rows = []
    with SessionLocal() as db:
        feedback_rows = db.scalars(select(Feedback).where(Feedback.rating < 0)).all()
        for feedback in feedback_rows:
            message = db.get(Message, feedback.message_id)
            recommendation = (
                db.scalars(
                    select(RecommendationLog).where(RecommendationLog.message_id == feedback.message_id)
                ).first()
            )
            rows.append(
                {
                    "feedback_id": feedback.id,
                    "message_id": feedback.message_id,
                    "session_id": message.session_id if message else "",
                    "answer": message.content if message else "",
                    "reason": feedback.reason,
                    "products_json": recommendation.products_json if recommendation else "[]",
                    "created_at": feedback.created_at.isoformat(),
                }
            )
    write_csv(output_dir / "feedback_failures.csv", rows)
    reason_counts = Counter(row["reason"] or "未填写" for row in rows)
    write_markdown_report(
        output_dir / "feedback_failure_report.md",
        "Feedback Failure Report",
        {"negative_feedback_count": len(rows), **dict(reason_counts)},
        rows,
    )
    return rows
