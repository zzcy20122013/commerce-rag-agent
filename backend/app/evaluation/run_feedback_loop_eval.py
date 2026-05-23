import argparse
import json
from pathlib import Path
from typing import Any

from app.evaluation.feedback_loop_eval_metrics import analyze_feedback_rows, build_feedback_failures
from app.evaluation.report import write_csv, write_markdown_report
from app.models.db import SessionLocal, init_db
from app.models.tables import ChatSession, Feedback, Message, RecommendationLog


BACKEND_ROOT = Path(__file__).resolve().parents[2]
PROJECT_ROOT = BACKEND_ROOT.parent
DEFAULT_CASES_PATH = BACKEND_ROOT / "app" / "evaluation" / "datasets" / "feedback_loop_eval_cases.json"
DEFAULT_REPORT_DIR = PROJECT_ROOT / "docs" / "evaluation" / "reports"
EVAL_PREFIX = "feedback_eval_"


def run_feedback_loop_evaluation(
    *,
    cases_path: str | Path = DEFAULT_CASES_PATH,
    report_dir: str | Path = DEFAULT_REPORT_DIR,
) -> dict[str, Any]:
    cases = _load_cases(cases_path)
    report_path = Path(report_dir)

    init_db()
    with SessionLocal() as db:
        _cleanup_eval_rows(db)
        rows = _insert_eval_feedback_rows(db, cases)
        summary = analyze_feedback_rows(rows)
        failures = build_feedback_failures(rows)
        _cleanup_eval_rows(db)

    write_csv(report_path / "feedback_loop_eval_details.csv", rows)
    write_markdown_report(report_path / "feedback_loop_eval_report.md", "Feedback Loop Evaluation Report", summary, failures)
    return {"metrics": summary, "report_dir": str(report_path)}


def _load_cases(path: str | Path) -> list[dict[str, Any]]:
    with Path(path).open("r", encoding="utf-8") as source:
        data = json.load(source)
    if not isinstance(data, list):
        raise ValueError("feedback loop eval dataset must be a JSON array")
    return data


def _insert_eval_feedback_rows(db, cases: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for index, case in enumerate(cases, start=1):
        session_id = f"{EVAL_PREFIX}session_{index:03d}"
        user_message_id = f"{EVAL_PREFIX}user_msg_{index:03d}"
        assistant_message_id = f"{EVAL_PREFIX}assistant_msg_{index:03d}"
        feedback_id = f"{EVAL_PREFIX}fb_{index:03d}"

        session = ChatSession(id=session_id, user_id="feedback-eval", title=f"反馈评测 {index}")
        user_message = Message(id=user_message_id, session_id=session_id, role="user", content=str(case.get("query", "")))
        assistant_message = Message(
            id=assistant_message_id,
            session_id=session_id,
            role="assistant",
            content=str(case.get("answer", "")),
        )
        feedback = Feedback(
            id=feedback_id,
            message_id=assistant_message_id,
            rating=int(case.get("rating", 0)),
            reason=str(case.get("reason", "")),
        )
        recommendation = RecommendationLog(
            id=f"{EVAL_PREFIX}rec_{index:03d}",
            session_id=session_id,
            message_id=assistant_message_id,
            products_json=json.dumps(case.get("products") or [], ensure_ascii=False),
        )
        db.add_all([session, user_message, assistant_message, feedback, recommendation])
        rows.append(
            {
                "feedback_id": feedback_id,
                "message_id": assistant_message_id,
                "session_id": session_id,
                "query": user_message.content,
                "answer": assistant_message.content,
                "rating": feedback.rating,
                "reason": feedback.reason,
                "products_json": recommendation.products_json,
            }
        )
    db.commit()
    return rows


def _cleanup_eval_rows(db) -> None:
    db.query(Feedback).filter(Feedback.id.like(f"{EVAL_PREFIX}%")).delete(synchronize_session=False)
    db.query(RecommendationLog).filter(RecommendationLog.id.like(f"{EVAL_PREFIX}%")).delete(synchronize_session=False)
    db.query(Message).filter(Message.id.like(f"{EVAL_PREFIX}%")).delete(synchronize_session=False)
    db.query(ChatSession).filter(ChatSession.id.like(f"{EVAL_PREFIX}%")).delete(synchronize_session=False)
    db.commit()


def main() -> None:
    parser = argparse.ArgumentParser(description="Run feedback loop evaluation.")
    parser.add_argument("--cases", default=str(DEFAULT_CASES_PATH), help="Path to feedback loop JSON cases.")
    parser.add_argument("--report-dir", default=str(DEFAULT_REPORT_DIR), help="Report output directory.")
    args = parser.parse_args()
    print(run_feedback_loop_evaluation(cases_path=args.cases, report_dir=args.report_dir))


if __name__ == "__main__":
    main()
