import json
from typing import Any

from app.models.tables import Product
from app.services.business_rules import rule_dict


def build_review_insight(product: Product, memory: dict | None = None) -> dict:
    summary = _safe_specs(product).get("review_summary") or {}
    if not isinstance(summary, dict):
        return {}
    positive_keywords = _clean_list(summary.get("positive_keywords") or summary.get("positive_tags") or [])
    negative_keywords = _clean_list(
        summary.get("risk_tags") or summary.get("negative_keywords") or summary.get("negative_tags") or []
    )
    negative_review_count = _safe_int(summary.get("negative_review_count"))
    negative_reviews = _clean_list(summary.get("representative_negative_reviews") or [])
    positive_reviews = _clean_list(summary.get("representative_positive_reviews") or [])
    dimensions = _dimension_summary(
        product,
        memory or {},
        " ".join([*positive_keywords, *negative_keywords, *positive_reviews, *negative_reviews]),
    )
    if not any([positive_keywords, negative_keywords, negative_review_count, negative_reviews, positive_reviews, dimensions]):
        return {}
    return {
        "positive_keywords": positive_keywords[:5],
        "negative_keywords": negative_keywords[:5],
        "negative_review_count": negative_review_count,
        "representative_positive_reviews": positive_reviews[:2],
        "representative_negative_reviews": negative_reviews[:2],
        "dimensions": dimensions,
    }


def format_positive_review_evidence(insight: dict) -> str:
    keywords = _clean_list(insight.get("positive_keywords") or [])
    snippets = _clean_list(insight.get("representative_positive_reviews") or [])
    parts = []
    if keywords:
        parts.append(f"高频正向：{'、'.join(keywords[:3])}")
    if snippets:
        parts.append(f"代表评价：{snippets[0][:36]}")
    return "；".join(parts)


def _safe_specs(product: Product) -> dict[str, Any]:
    try:
        parsed = json.loads(product.specs_json or "{}")
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _dimension_summary(product: Product, memory: dict, text: str) -> dict[str, str]:
    subcategory = str(memory.get("subcategory") or _infer_subcategory(product.title)).strip()
    keyword_map = rule_dict("review_insight", "dimension_keywords").get(subcategory)
    if not isinstance(keyword_map, dict):
        return {}
    result: dict[str, str] = {}
    for dimension, raw_keywords in keyword_map.items():
        keywords = _clean_list(raw_keywords)
        hits = sum(text.count(keyword) for keyword in keywords if keyword)
        if hits >= 2:
            result[str(dimension)] = "反馈较多"
        elif hits == 1:
            result[str(dimension)] = "有提及"
        else:
            result[str(dimension)] = "证据不足"
    return result


def _infer_subcategory(title: str) -> str:
    aliases = {
        "平板": ["平板", "Pad", "pad"],
        "防晒": ["防晒"],
        "鞋": ["鞋", "跑鞋"],
        "早餐": ["早餐", "麦片", "代餐"],
    }
    for subcategory, keywords in aliases.items():
        if any(keyword in title for keyword in keywords):
            return subcategory
    return ""


def _clean_list(values: Any) -> list[str]:
    if not isinstance(values, list):
        return []
    return list(dict.fromkeys(str(value).strip() for value in values if str(value).strip()))


def _safe_int(value: Any) -> int:
    try:
        return max(int(value or 0), 0)
    except (TypeError, ValueError):
        return 0
