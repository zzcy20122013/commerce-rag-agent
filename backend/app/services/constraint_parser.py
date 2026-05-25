"""Parse negative shopping constraints from natural-language queries."""

from __future__ import annotations

import json
import re
from typing import Any


PUNCTUATION = r"，,。.!！；;、"
PRODUCT_ID_PATTERN = re.compile(r"\b(p_[a-zA-Z0-9_]+)\b")

EXCLUDE_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(rf"(?:不要|不想要|不接受|排除)\s*([^ {PUNCTUATION}]{{1,30}}?品牌)"), "exclude_brand"),
    (re.compile(rf"(?:不要|不想要|不接受|排除|别给我|别要|不想看)\s*([^ {PUNCTUATION}]{{1,30}}?牌子)"), "exclude_brand"),
    (re.compile(rf"非\s*([^ {PUNCTUATION}]{{1,30}}?)\s*品牌"), "exclude_brand"),
    (re.compile(rf"(?:不含|不要含|不能含|无)\s*([^ {PUNCTUATION}]{{1,30}})"), "exclude_ingredient"),
    (re.compile(rf"(?:不要|不想要|不接受|除了|排除)\s*([^ {PUNCTUATION}]{{1,30}})"), "exclude"),
]

NEGATION_PREFIXES = ["无", "不含", "没有", "未添加", "0", "零"]


def parse_constraints(query: str) -> dict[str, Any]:
    text = (query or "").strip()
    exclude_brands: list[str] = []
    exclude_ingredients: list[str] = []
    exclude_product_ids = list(dict.fromkeys(PRODUCT_ID_PATTERN.findall(text)))
    exclusions: list[dict[str, str]] = []

    for pattern, kind in EXCLUDE_PATTERNS:
        for match in pattern.finditer(text):
            value = _clean_value(match.group(1))
            if not value:
                continue
            entry = {"kind": kind, "value": value, "raw": match.group(0)}
            exclusions = merge_exclusions(exclusions, [entry])
            if kind == "exclude_brand":
                brand = _brand_value(value)
                if brand and brand not in exclude_brands:
                    exclude_brands.append(brand)
            elif kind == "exclude_ingredient":
                if value not in exclude_ingredients:
                    exclude_ingredients.append(value)

    return {
        "exclude_brands": exclude_brands,
        "exclude_ingredients": exclude_ingredients,
        "exclude_product_ids": exclude_product_ids,
        "exclusions": exclusions,
    }


def merge_exclusions(previous: list[dict] | None, new: list[dict] | None) -> list[dict]:
    merged: list[dict] = []
    seen: set[str] = set()
    for source in [previous or [], new or []]:
        for item in source:
            kind = str(item.get("kind") or "exclude")
            value = _clean_value(str(item.get("value") or ""))
            if not value:
                continue
            key = _normal_key(value)
            if key in seen:
                continue
            seen.add(key)
            merged.append({"kind": kind, "value": value, "raw": str(item.get("raw") or value)})
    return merged


def product_is_excluded(
    title: str,
    brand: str,
    description: str,
    specs_json: str = "",
    exclusions: list[dict] | None = None,
) -> bool:
    specs_values = _flatten_specs_values(specs_json)
    searchable = " ".join([title or "", brand or "", description or "", " ".join(specs_values)]).lower()
    for item in exclusions or []:
        value = _clean_value(str(item.get("value") or ""))
        if not value:
            continue
        kind = str(item.get("kind") or "exclude")
        normalized = value.lower()
        if kind == "exclude_brand":
            brand_term = _brand_value(value).lower()
            if brand_term and (brand_term in (brand or "").lower() or brand_term in searchable):
                return True
            continue
        if kind == "exclude_ingredient":
            if _matches_specs_value(normalized, specs_values):
                return True
            if _contains_unnegated((description or "").lower(), normalized):
                return True
            continue
        if len(normalized) >= 2 and _contains_unnegated(searchable, normalized):
            return True
    return False


def _clean_value(value: str) -> str:
    cleaned = (value or "").strip()
    cleaned = cleaned.strip(" ，,。.!！；;、")
    for prefix in ["也", "都", "再"]:
        if cleaned.startswith(prefix) and len(cleaned) > len(prefix):
            cleaned = cleaned[len(prefix):].strip()
    return cleaned


def _brand_value(value: str) -> str:
    return _clean_value(value).replace("品牌", "").replace("牌子", "").strip()


def _normal_key(value: str) -> str:
    return value.replace("品牌", "").replace("牌子", "").replace("的", "").strip().lower()


def _contains_unnegated(text: str, value: str) -> bool:
    if not value or value not in text:
        return False
    start = 0
    while True:
        index = text.find(value, start)
        if index < 0:
            return False
        prefix = text[max(0, index - 4):index]
        if not any(prefix.endswith(marker) for marker in NEGATION_PREFIXES):
            return True
        start = index + len(value)


def _matches_specs_value(value: str, specs_values: list[str]) -> bool:
    for item in specs_values:
        lowered = item.lower()
        if value in lowered and _contains_unnegated(lowered, value):
            return True
    return False


def _flatten_specs_values(specs_json: str) -> list[str]:
    try:
        parsed = json.loads(specs_json or "{}")
    except json.JSONDecodeError:
        return [specs_json] if specs_json else []
    values: list[str] = []

    def collect(node: Any) -> None:
        if isinstance(node, dict):
            for value in node.values():
                collect(value)
        elif isinstance(node, list):
            for value in node:
                collect(value)
        elif node is not None:
            values.append(str(node))

    collect(parsed)
    return values
