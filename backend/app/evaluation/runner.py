import csv
from pathlib import Path
from typing import Any

from app.agents.graph import run_agent
from app.agents.intent_router import classify_intent
from app.evaluation.metrics import (
    accuracy,
    constraint_satisfaction,
    memory_constraint_inheritance,
    multi_turn_consistency,
    recall_at_k,
)
from app.evaluation.report import write_csv, write_markdown_report
from app.models.db import SessionLocal, init_db
from app.retrieval.image_index import ImageIndex
from app.retrieval.text_index import TextIndex
from app.scripts.seed_products import seed_product_images, seed_products


BACKEND_ROOT = Path(__file__).resolve().parents[2]
PROJECT_ROOT = BACKEND_ROOT.parent
CASES_DIR = BACKEND_ROOT / "app" / "evaluation" / "cases"
DEFAULT_REPORT_DIR = PROJECT_ROOT / "docs" / "reports"


def run_all_evaluations(report_dir: str | Path = DEFAULT_REPORT_DIR) -> dict[str, Any]:
    report_path = Path(report_dir)
    init_db()
    with SessionLocal() as db:
        seed_products(db)
        seed_product_images(db)
        text_index = TextIndex()
        text_index.index_products(db)
        text_index.index_faqs()
        image_index = ImageIndex()
        image_index.index_product_images(db)

        intent_summary = run_intent_eval(report_path)
        text_summary = run_text_retrieval_eval(text_index, report_path)
        image_summary = run_image_retrieval_eval(image_index, report_path)
        recommendation_summary = run_recommendation_eval(db, report_path)
        multi_turn_summary = run_multi_turn_eval(db, report_path)

    metrics = {
        **intent_summary,
        **text_summary,
        **image_summary,
        **recommendation_summary,
        **multi_turn_summary,
    }
    write_markdown_report(report_path / "eval-summary.md", "Evaluation Summary", metrics, [])
    return {"metrics": metrics, "report_dir": str(report_path)}


def run_intent_eval(report_dir: Path) -> dict[str, float]:
    rows = _read_cases("intent_cases.csv")
    predictions = []
    labels = []
    failures = []
    for row in rows:
        predicted = classify_intent(row["query"]).intent
        expected = row["expected_intent"]
        predictions.append(predicted)
        labels.append(expected)
        if predicted != expected:
            failures.append({"case_id": row["case_id"], "query": row["query"], "expected": expected, "actual": predicted})
    write_csv(report_dir / "intent_failures.csv", failures)
    return {"intent_accuracy": round(accuracy(predictions, labels), 4)}


def run_text_retrieval_eval(index: TextIndex, report_dir: Path) -> dict[str, float]:
    rows = _read_cases("text_retrieval_cases.csv")
    metrics = {"text_recall@1": [], "text_recall@3": [], "text_recall@5": []}
    failures = []
    for row in rows:
        product_hits = index.search_products(row["query"], limit=5)
        faq_hits = index.search_faq(row["query"], limit=5)
        hits = product_hits + faq_hits
        expected = _split_ids(row.get("expected_product_ids")) + _split_ids(row.get("expected_doc_ids"))
        for k in [1, 3, 5]:
            score = recall_at_k(hits, expected, k)
            metrics[f"text_recall@{k}"].append(score)
        if recall_at_k(hits, expected, 5) == 0:
            failures.append({"case_id": row["case_id"], "query": row["query"], "expected": "|".join(expected), "actual": _ids(hits)})
    result = {key: round(sum(values) / len(values), 4) if values else 0.0 for key, values in metrics.items()}
    write_markdown_report(report_dir / "text_retrieval_report.md", "Text Retrieval Report", result, failures)
    return result


def run_image_retrieval_eval(index: ImageIndex, report_dir: Path) -> dict[str, float]:
    rows = _read_cases("image_retrieval_cases.csv")
    metrics = {"image_recall@1": [], "image_recall@5": [], "image_recall@10": []}
    failures = []
    for row in rows:
        image_path = BACKEND_ROOT / row["image_path"]
        if not image_path.exists():
            failures.append({"case_id": row["case_id"], "query": str(image_path), "expected": row["expected_product_ids"], "actual": "missing_image"})
            for k in [1, 5, 10]:
                metrics[f"image_recall@{k}"].append(0.0)
            continue
        hits = index.search_by_image(str(image_path), limit=10)
        expected = _split_ids(row.get("expected_product_ids"))
        for k in [1, 5, 10]:
            metrics[f"image_recall@{k}"].append(recall_at_k(hits, expected, k))
        if recall_at_k(hits, expected, 10) == 0:
            failures.append({"case_id": row["case_id"], "query": str(image_path), "expected": "|".join(expected), "actual": _ids(hits)})
    result = {key: round(sum(values) / len(values), 4) if values else 0.0 for key, values in metrics.items()}
    write_markdown_report(report_dir / "image_retrieval_report.md", "Image Retrieval Report", result, failures)
    return result


def run_recommendation_eval(db, report_dir: Path) -> dict[str, float]:
    rows = _read_cases("recommendation_cases.csv")
    passes = []
    price_passes = []
    stock_passes = []
    failures = []
    for row in rows:
        result = run_agent(db, row["query"])
        constraints = {"budget_max": _int_or_none(row.get("budget_max")), "category": row.get("category")}
        cards = result.get("product_cards", [])
        check = constraint_satisfaction(cards, constraints)
        passes.append(1.0 if check["passed"] and cards else 0.0)
        price_passes.append(1.0 if not check["failed_product_ids"] else 0.0)
        stock_passes.append(1.0 if all(card.get("stock_status") == "in_stock" for card in cards) else 0.0)
        if not check["passed"]:
            failures.append({"case_id": row["case_id"], "query": row["query"], "expected": str(constraints), "actual": str(check)})
    metrics = {
        "recommendation_hit_rate": _avg(passes),
        "price_constraint_rate": _avg(price_passes),
        "stock_constraint_rate": _avg(stock_passes),
    }
    write_markdown_report(report_dir / "recommendation_report.md", "Recommendation Report", metrics, failures)
    return metrics


def run_multi_turn_eval(db, report_dir: Path) -> dict[str, float]:
    rows = _read_cases("multi_turn_cases.csv")
    inheritance = []
    consistency = []
    failures = []
    for row in rows:
        first = run_agent(db, row["turn_1"])
        second = run_agent(db, row["turn_2"], memory=first.get("memory", {}))
        expected = _parse_memory(row["expected_memory"])
        memory_result = memory_constraint_inheritance(second.get("memory", {}), expected)
        turn_result = multi_turn_consistency(second, expected)
        inheritance.append(1.0 if memory_result["passed"] else 0.0)
        consistency.append(1.0 if turn_result["passed"] else 0.0)
        if not turn_result["passed"]:
            failures.append({"case_id": row["case_id"], "query": row["turn_2"], "expected": row["expected_memory"], "actual": str(second.get("memory", {}))})
    metrics = {
        "multi_turn_memory_inheritance": _avg(inheritance),
        "multi_turn_consistency": _avg(consistency),
    }
    write_markdown_report(report_dir / "multi_turn_report.md", "Multi Turn Report", metrics, failures)
    return metrics


def _read_cases(filename: str) -> list[dict[str, str]]:
    with (CASES_DIR / filename).open("r", encoding="utf-8", newline="") as source:
        return list(csv.DictReader(source))


def _split_ids(value: str | None) -> list[str]:
    return [item for item in (value or "").split("|") if item]


def _ids(results: list[dict[str, Any]]) -> str:
    return "|".join(str(item.get("product_id") or item.get("id") or item.get("metadata", {}).get("product_id") or "") for item in results)


def _parse_memory(raw: str) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for part in raw.split(";"):
        if not part or "=" not in part:
            continue
        key, value = part.split("=", 1)
        if key == "budget_max":
            result[key] = int(value)
        elif key in {"use_cases", "preferences"}:
            result[key] = value.split("|")
        elif "|" in value:
            result[key] = value.split("|")
        else:
            result[key] = value
    return result


def _int_or_none(value: str | None) -> int | None:
    return int(value) if value else None


def _avg(values: list[float]) -> float:
    return round(sum(values) / len(values), 4) if values else 0.0
