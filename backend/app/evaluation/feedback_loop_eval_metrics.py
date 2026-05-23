from collections import Counter
from typing import Any


def analyze_feedback_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(rows)
    positives = [row for row in rows if _to_int(row.get("rating")) > 0]
    negatives = [row for row in rows if _to_int(row.get("rating")) < 0]
    negative_with_reason = [row for row in negatives if str(row.get("reason") or "").strip()]
    reason_counts = Counter(str(row.get("reason") or "未填写") for row in negatives)

    summary: dict[str, Any] = {
        "feedback_total": total,
        "feedback_positive_count": len(positives),
        "feedback_negative_count": len(negatives),
        "feedback_positive_rate": _rate(len(positives), total),
        "feedback_negative_rate": _rate(len(negatives), total),
        "feedback_negative_reason_coverage": _rate(len(negative_with_reason), len(negatives)),
    }
    for reason, count in sorted(reason_counts.items()):
        summary[f"reason_{reason}"] = count
    return summary


def build_feedback_failures(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    failures = []
    for row in rows:
        if _to_int(row.get("rating")) >= 0:
            continue
        failures.append(
            {
                "case_id": row.get("feedback_id", ""),
                "query": row.get("query", ""),
                "expected": row.get("reason", "") or "未填写",
                "actual": row.get("answer", ""),
            }
        )
    return failures


def _rate(count: int, total: int) -> float:
    return round(count / total, 4) if total else 0.0


def _to_int(value: Any) -> int:
    if value in {None, ""}:
        return 0
    return int(value)
