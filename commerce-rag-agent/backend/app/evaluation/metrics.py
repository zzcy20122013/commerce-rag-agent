from collections.abc import Iterable
from typing import Any


def accuracy(predictions: list[str], labels: list[str]) -> float:
    if not labels:
        return 0.0
    correct = sum(1 for predicted, label in zip(predictions, labels) if predicted == label)
    return correct / len(labels)


def recall_at_k(results: list[dict[str, Any]], expected_ids: Iterable[str], k: int) -> float:
    expected = set(expected_ids)
    if not expected:
        return 0.0
    top_ids = {_result_id(item) for item in results[:k]}
    return 1.0 if expected & top_ids else 0.0


def constraint_satisfaction(products: list[dict[str, Any]], constraints: dict[str, Any]) -> dict[str, Any]:
    failed = []
    budget_max = _to_int(constraints.get("budget_max"))
    category = constraints.get("category")
    for product in products:
        product_id = _result_id(product)
        if budget_max is not None and _to_int(product.get("price")) > budget_max:
            failed.append(product_id)
            continue
        if category and product.get("category") and product.get("category") != category:
            failed.append(product_id)
            continue
        stock = product.get("stock")
        stock_status = product.get("stock_status")
        if stock is not None and _to_int(stock) <= 0:
            failed.append(product_id)
            continue
        if stock_status == "out_of_stock":
            failed.append(product_id)
    return {"passed": not failed, "failed_product_ids": failed}


def memory_constraint_inheritance(actual_memory: dict[str, Any], expected_memory: dict[str, Any]) -> dict[str, Any]:
    missing = []
    for key, expected_value in expected_memory.items():
        actual_value = actual_memory.get(key)
        if isinstance(expected_value, list):
            actual_values = set(actual_value or [])
            if not set(expected_value).issubset(actual_values):
                missing.append(key)
        elif actual_value != expected_value:
            missing.append(key)
    return {"passed": not missing, "missing_fields": missing}


def multi_turn_consistency(turn_result: dict[str, Any], expected_constraints: dict[str, Any]) -> dict[str, Any]:
    memory_result = memory_constraint_inheritance(turn_result.get("memory", {}), expected_constraints)
    product_result = constraint_satisfaction(turn_result.get("product_cards", []), expected_constraints)
    return {
        "passed": memory_result["passed"] and product_result["passed"],
        "memory": memory_result,
        "products": product_result,
    }


def positive_feedback_rate(feedback_rows: list[dict[str, Any]]) -> float:
    if not feedback_rows:
        return 0.0
    positives = sum(1 for row in feedback_rows if _to_int(row.get("rating")) > 0)
    return positives / len(feedback_rows)


def _result_id(item: dict[str, Any]) -> str:
    metadata = item.get("metadata") or {}
    return str(
        item.get("product_id")
        or metadata.get("product_id")
        or metadata.get("document_id")
        or metadata.get("image_id")
        or item.get("id")
        or ""
    )


def _to_int(value: Any) -> int | None:
    if value in {None, ""}:
        return None
    return int(value)
