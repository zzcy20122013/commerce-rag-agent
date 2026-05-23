import json
from pathlib import Path
from typing import Any


GUIDE_INTENTS = {"shopping_guide", "decision_guide", "compare"}
SYSTEM_TERMS = {
    "候选商品",
    "本次检索",
    "筛选结果",
    "商品ID",
    "sub_category",
    "sku_count",
    "price_range",
    "retrieved_items",
}
GUIDE_TONE_TERMS = {
    "更推荐",
    "我更推荐",
    "更建议",
    "主推",
    "优先",
    "备选",
    "我会先看",
    "先看",
    "不太建议",
    "不太推荐",
    "如果你更在意",
    "适合你",
    "建议",
    "取舍",
}
NO_EXACT_TERMS = {
    "没有严格",
    "没有完全符合",
    "没有找到严格",
    "暂时没有",
    "不硬推",
    "超出预算",
    "加预算",
    "退一步",
}


def load_guide_eval_cases(path: str | Path) -> list[dict[str, Any]]:
    with Path(path).open("r", encoding="utf-8") as source:
        data = json.load(source)
    if not isinstance(data, list):
        raise ValueError("guide eval dataset must be a JSON array")
    return data


def score_guide_case(case: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
    answer = str(result.get("answer") or "")
    cards = list(result.get("product_cards") or [])
    expected_intent = case.get("expected_intent")
    expects_no_exact = bool(case.get("expected_no_exact_match", False))

    checks = {
        "intent_ok": _intent_ok(expected_intent, result.get("intent")),
        "card_ok": _card_ok(case, cards),
        "term_ok": _term_ok(case, result),
        "budget_ok": _budget_ok(case, cards),
        "no_exact_match_ok": _no_exact_match_ok(expects_no_exact, result, answer),
        "style_ok": _style_ok(expected_intent, expects_no_exact, answer),
        "memory_ok": _memory_ok(case, result.get("memory") or {}),
        "cart_ok": _cart_ok(case, result),
    }
    failed_checks = [name for name, passed in checks.items() if not passed]
    return {
        "case_id": case.get("case_id", ""),
        "scenario": case.get("scenario", ""),
        "passed": not failed_checks,
        "failed_checks": failed_checks,
        **checks,
    }


def summarize_guide_results(scored_cases: list[dict[str, Any]]) -> dict[str, float]:
    return {
        "guide_total_cases": len(scored_cases),
        "guide_pass_rate": _rate(scored_cases, "passed"),
        "guide_intent_rate": _rate(scored_cases, "intent_ok"),
        "guide_card_rate": _rate(scored_cases, "card_ok"),
        "guide_term_rate": _rate(scored_cases, "term_ok"),
        "guide_budget_rate": _rate(scored_cases, "budget_ok"),
        "guide_no_exact_rate": _rate(scored_cases, "no_exact_match_ok"),
        "guide_style_rate": _rate(scored_cases, "style_ok"),
        "guide_memory_rate": _rate(scored_cases, "memory_ok"),
        "guide_cart_rate": _rate(scored_cases, "cart_ok"),
    }


def _intent_ok(expected: str | None, actual: str | None) -> bool:
    return not expected or expected == actual


def _card_ok(case: dict[str, Any], cards: list[dict[str, Any]]) -> bool:
    min_cards = int(case.get("min_cards") or 0)
    return len(cards) >= min_cards


def _term_ok(case: dict[str, Any], result: dict[str, Any]) -> bool:
    expected_terms = [str(term) for term in case.get("expected_terms") or [] if str(term)]
    if not expected_terms:
        return True
    haystack = _result_text(result)
    return any(term in haystack for term in expected_terms)


def _budget_ok(case: dict[str, Any], cards: list[dict[str, Any]]) -> bool:
    budget = case.get("budget_max")
    if budget in {None, ""} or bool(case.get("expected_no_exact_match", False)):
        return True
    return all(_to_int(card.get("price")) <= int(budget) for card in cards)


def _no_exact_match_ok(expects_no_exact: bool, result: dict[str, Any], answer: str) -> bool:
    if not expects_no_exact:
        return not bool(result.get("no_exact_match"))
    return bool(result.get("no_exact_match")) and any(term in answer for term in NO_EXACT_TERMS)


def _style_ok(expected_intent: str | None, expects_no_exact: bool, answer: str) -> bool:
    if expected_intent not in GUIDE_INTENTS and not expects_no_exact:
        return True
    if not answer.strip():
        return False
    if any(term in answer for term in SYSTEM_TERMS):
        return False
    if expected_intent in GUIDE_INTENTS and not any(term in answer for term in GUIDE_TONE_TERMS):
        return False
    if expects_no_exact and not any(term in answer for term in NO_EXACT_TERMS):
        return False
    return True


def _memory_ok(case: dict[str, Any], memory: dict[str, Any]) -> bool:
    expected_terms = [str(term) for term in case.get("expected_memory_terms") or [] if str(term)]
    if not expected_terms:
        return True
    memory_text = json.dumps(memory, ensure_ascii=False, sort_keys=True)
    return all(term in memory_text for term in expected_terms)


def _cart_ok(case: dict[str, Any], result: dict[str, Any]) -> bool:
    expected = case.get("expected_cart") or {}
    if not expected:
        return True
    answer = str(result.get("answer") or "")
    retrieved_items = result.get("retrieved_items") or []
    if expected.get("action") and str(expected["action"]) not in answer and result.get("intent") != "purchase_help":
        return False
    if expected.get("min_items") is not None and len(retrieved_items) < int(expected["min_items"]):
        return False
    if expected.get("quantity") is not None:
        quantity = int(expected["quantity"])
        if f"x {quantity}" in answer or f"数量改成 {quantity}" in answer or f"{quantity} 件" in answer:
            return True
        return any(_to_int(item.get("quantity")) == quantity for item in retrieved_items)
    return True


def _result_text(result: dict[str, Any]) -> str:
    card_text = " ".join(
        " ".join(str(card.get(field) or "") for field in ("title", "subtitle", "reasons"))
        for card in result.get("product_cards") or []
    )
    return f"{result.get('answer', '')} {card_text}"


def _rate(rows: list[dict[str, Any]], key: str) -> float:
    if not rows:
        return 0.0
    return round(sum(1 for row in rows if _as_bool(row.get(key))) / len(rows), 4)


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y"}
    return bool(value)


def _to_int(value: Any) -> int:
    if value in {None, ""}:
        return 0
    return int(value)
