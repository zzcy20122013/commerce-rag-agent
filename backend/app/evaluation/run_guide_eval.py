import argparse
import csv
from pathlib import Path
from typing import Any

from app.agents.graph import run_agent
from app.evaluation.guide_eval_metrics import (
    load_guide_eval_cases,
    score_guide_case,
    summarize_guide_results,
)
from app.evaluation.report import write_markdown_report
from app.models.db import SessionLocal, init_db
from app.models.tables import CartItem
from app.scripts.seed_products import seed_product_images, seed_products


BACKEND_ROOT = Path(__file__).resolve().parents[2]
PROJECT_ROOT = BACKEND_ROOT.parent
DEFAULT_CASES_PATH = BACKEND_ROOT / "app" / "evaluation" / "datasets" / "guide_eval_cases.json"
DEFAULT_REPORT_DIR = PROJECT_ROOT / "docs" / "evaluation" / "reports"


def run_guide_evaluation(
    *,
    cases_path: str | Path = DEFAULT_CASES_PATH,
    report_dir: str | Path = DEFAULT_REPORT_DIR,
) -> dict[str, Any]:
    cases = load_guide_eval_cases(cases_path)
    report_path = Path(report_dir)
    details: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []

    init_db()
    with SessionLocal() as db:
        seed_products(db)
        seed_product_images(db)
        for case in cases:
            _reset_cart(db)
            memory: dict[str, Any] = {}
            result: dict[str, Any] = {}
            for turn in case.get("turns") or [case.get("query", "")]:
                result = run_agent(db, str(turn), memory=memory)
                memory = result.get("memory", {})

            scored = score_guide_case(case, result)
            details.append(_detail_row(case, result, scored))
            if not scored["passed"]:
                failures.append(
                    {
                        "case_id": case.get("case_id", ""),
                        "query": " / ".join(case.get("turns") or [case.get("query", "")]),
                        "expected": ",".join(scored["failed_checks"]),
                        "actual": result.get("answer", ""),
                    }
                )

    metrics = summarize_guide_results(details)
    _write_details_csv(report_path / "guide_eval_details.csv", details)
    write_markdown_report(report_path / "guide_eval_report.md", "Guide Evaluation Report", metrics, failures)
    return {"metrics": metrics, "report_dir": str(report_path)}


def _detail_row(case: dict[str, Any], result: dict[str, Any], scored: dict[str, Any]) -> dict[str, Any]:
    return {
        "case_id": case.get("case_id", ""),
        "scenario": case.get("scenario", ""),
        "turn_count": len(case.get("turns") or [case.get("query", "")]),
        "expected_intent": case.get("expected_intent", ""),
        "actual_intent": result.get("intent", ""),
        "passed": _csv_bool(scored["passed"]),
        "failed_checks": "|".join(scored["failed_checks"]),
        "intent_ok": _csv_bool(scored["intent_ok"]),
        "card_ok": _csv_bool(scored["card_ok"]),
        "term_ok": _csv_bool(scored["term_ok"]),
        "budget_ok": _csv_bool(scored["budget_ok"]),
        "no_exact_match_ok": _csv_bool(scored["no_exact_match_ok"]),
        "style_ok": _csv_bool(scored["style_ok"]),
        "memory_ok": _csv_bool(scored["memory_ok"]),
        "cart_ok": _csv_bool(scored["cart_ok"]),
        "card_count": len(result.get("product_cards") or []),
        "answer": result.get("answer", ""),
    }


def _write_details_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "case_id",
        "scenario",
        "turn_count",
        "expected_intent",
        "actual_intent",
        "passed",
        "failed_checks",
        "intent_ok",
        "card_ok",
        "term_ok",
        "budget_ok",
        "no_exact_match_ok",
        "style_ok",
        "memory_ok",
        "cart_ok",
        "card_count",
        "answer",
    ]
    with path.open("w", encoding="utf-8", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _reset_cart(db) -> None:
    db.query(CartItem).delete()
    db.commit()


def _csv_bool(value: bool) -> str:
    return "true" if value else "false"


def main() -> None:
    parser = argparse.ArgumentParser(description="Run guide-focused commerce agent evaluation.")
    parser.add_argument("--cases", default=str(DEFAULT_CASES_PATH), help="Path to guide eval JSON cases.")
    parser.add_argument("--report-dir", default=str(DEFAULT_REPORT_DIR), help="Report output directory.")
    args = parser.parse_args()
    print(run_guide_evaluation(cases_path=args.cases, report_dir=args.report_dir))


if __name__ == "__main__":
    main()
