import csv
from contextlib import contextmanager
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
from app.models.tables import Product
from app.retrieval.image_index import ImageIndex
from app.retrieval.text_index import TextIndex
from app.scripts.seed_products import seed_product_images, seed_products


BACKEND_ROOT = Path(__file__).resolve().parents[2]
PROJECT_ROOT = BACKEND_ROOT.parent
CASES_DIR = BACKEND_ROOT / "app" / "evaluation" / "cases"
DEFAULT_REPORT_DIR = PROJECT_ROOT / "docs" / "evaluation" / "reports"


def run_all_evaluations(report_dir: str | Path = DEFAULT_REPORT_DIR) -> dict[str, Any]:
    report_path = Path(report_dir)
    init_db()
    with SessionLocal() as db:
        seed_products(db)
        seed_product_images(db)
        text_index = TextIndex()
        text_index.rebuild_products(db)
        text_index.rebuild_faqs()
        image_index = ImageIndex()
        image_index.rebuild_product_images(db)

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


def run_smoke_evaluation(report_dir: str | Path = DEFAULT_REPORT_DIR) -> dict[str, Any]:
    report_path = Path(report_dir)
    init_db()
    with SessionLocal() as db:
        seed_products(db)
        seed_product_images(db)
        text_index = TextIndex()
        text_index.rebuild_products(db)
        text_index.rebuild_faqs()
        metrics = run_smoke_eval(db, report_path)
    return {"metrics": metrics, "report_dir": str(report_path)}


def run_smoke_eval(db, report_dir: Path) -> dict[str, float]:
    rows = _read_cases("smoke_cases.csv")
    intent_scores = []
    constraint_scores = []
    style_scores = []
    no_exact_scores = []
    details = []
    failures = []

    for row in rows:
        with _stock_override_context(db, row.get("stock_zero_ids")):
            turns = _smoke_turns(row)
            memory: dict[str, Any] = {}
            result: dict[str, Any] = {}
            for turn in turns:
                result = run_agent(db, turn, memory=memory)
                memory = result.get("memory", {})
            query = turns[-1]

            expected_intent = row.get("expected_intent") or ""
            actual_intent = result.get("intent", "")
            intent_ok = not expected_intent or actual_intent == expected_intent
            intent_scores.append(1.0 if intent_ok else 0.0)

            cards = result.get("product_cards", [])
            constraints = {"budget_max": _int_or_none(row.get("budget_max")), "category": row.get("category")}
            constraint_check = constraint_satisfaction(cards, constraints)
            expects_no_exact = _bool_or_none(row.get("expected_no_exact_match"))
            has_constraints = constraints["budget_max"] is not None or bool(constraints["category"])
            actual_no_exact = bool(result.get("no_exact_match"))
            if expects_no_exact and actual_no_exact:
                constraint_ok = True
            else:
                constraint_ok = constraint_check["passed"] if cards else bool(expects_no_exact or not has_constraints)
            constraint_scores.append(1.0 if constraint_ok else 0.0)

            no_exact_ok = True if expects_no_exact is None else actual_no_exact == expects_no_exact
            if expects_no_exact is not None:
                no_exact_scores.append(1.0 if no_exact_ok else 0.0)

            style_check = _guide_style_check(
                result.get("answer", ""),
                expected_intent=expected_intent,
                expects_no_exact=bool(expects_no_exact),
            )
            style_scores.append(1.0 if style_check["passed"] else 0.0)

            detail = {
                "case_id": row["case_id"],
                "query": query,
                "turn_count": len(turns),
                "stock_zero_ids": row.get("stock_zero_ids", ""),
                "expected_intent": expected_intent,
                "actual_intent": actual_intent,
                "intent_ok": _csv_bool(intent_ok),
                "constraint_ok": _csv_bool(constraint_ok),
                "no_exact_match": _csv_bool(actual_no_exact),
                "no_exact_ok": _csv_bool(no_exact_ok),
                "style_ok": _csv_bool(style_check["passed"]),
                "style_reason": "|".join(style_check["reasons"]),
                "card_count": len(cards),
                "answer": result.get("answer", ""),
            }
            details.append(detail)
            if not (intent_ok and constraint_ok and no_exact_ok and style_check["passed"]):
                failures.append(
                    {
                        "case_id": row["case_id"],
                        "query": query,
                        "expected": row.get("expected_behavior", ""),
                        "actual": str(detail),
                    }
            )

    metrics = {
        "smoke_total_cases": float(len(rows)),
        "smoke_intent_accuracy": _avg(intent_scores),
        "smoke_constraint_rate": _avg(constraint_scores),
        "smoke_style_rate": _avg(style_scores),
        "smoke_no_exact_match_rate": _avg(no_exact_scores),
    }
    write_csv(report_dir / "smoke_eval_details.csv", details)
    write_markdown_report(report_dir / "smoke_eval_report.md", "Smoke Evaluation Report", metrics, failures)
    return metrics


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


def _smoke_turns(row: dict[str, str]) -> list[str]:
    turns = [
        (row.get(f"turn_{index}") or "").strip()
        for index in range(1, 5)
    ]
    turns = [turn for turn in turns if turn]
    if turns:
        return turns
    query = (row.get("query") or "").strip()
    if query:
        return [query]
    raise ValueError(f"Smoke case {row.get('case_id', '<unknown>')} has no query or turns")


@contextmanager
def _stock_override_context(db, raw_product_ids: str | None):
    original_stocks = {}
    for product_id in _split_ids(raw_product_ids):
        product = db.get(Product, product_id)
        if product is None:
            continue
        original_stocks[product_id] = product.stock
        product.stock = 0
    if original_stocks:
        db.flush()
    try:
        yield
    finally:
        for product_id, stock in original_stocks.items():
            product = db.get(Product, product_id)
            if product is not None:
                product.stock = stock
        if original_stocks:
            db.flush()


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


def _bool_or_none(value: str | None) -> bool | None:
    if value in {None, ""}:
        return None
    return value.strip().lower() in {"1", "true", "yes", "y"}


def _avg(values: list[float]) -> float:
    return round(sum(values) / len(values), 4) if values else 0.0


def _csv_bool(value: bool) -> str:
    return "true" if value else "false"


def _guide_style_check(answer: str, *, expected_intent: str, expects_no_exact: bool) -> dict[str, Any]:
    guide_intents = {"shopping_guide", "decision_guide", "compare"}
    if expected_intent not in guide_intents:
        return {"passed": True, "reasons": []}

    reasons = []
    forbidden_terms = [
        "候选商品",
        "本次检索",
        "综合评分",
        "筛选结果",
        "商品ID",
        "sub_category",
        "sku_count",
        "price_range",
        "faq_count",
        "review_count",
    ]
    guide_terms = [
        "更建议",
        "更推荐",
        "我更推荐",
        "主推",
        "优先",
        "备选",
        "不太建议",
        "不太推荐",
        "如果你更在意",
        "可以给你选",
        "给你推",
        "可以选",
        "没必要选",
        "挑",
        "退一步",
        "加预算",
        "建议",
    ]
    no_exact_terms = ["没有严格", "没有找到严格", "没有符合", "没有完全符合", "暂时没有", "超出预算", "加预算", "退一步"]

    if len(answer.strip()) < 12:
        reasons.append("answer_too_short")
    if any(term in answer for term in forbidden_terms):
        reasons.append("system_terms")
    if not any(term in answer for term in guide_terms):
        reasons.append("missing_guide_tone")
    if expects_no_exact and not any(term in answer for term in no_exact_terms):
        reasons.append("missing_no_exact_explanation")

    return {"passed": not reasons, "reasons": reasons}
