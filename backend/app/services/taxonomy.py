import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.models.tables import Product


TAXONOMY_PATH = Path(__file__).resolve().parents[1] / "data" / "taxonomy.json"
STRICT_FILTER_KEYWORDS = [
    "有哪些",
    "哪些",
    "有什么",
    "有哪几款",
    "列出",
    "清单",
    "不能超",
    "别超",
    "不超",
    "不要超",
    "绝对不能超",
    "卡死",
    "必须以内",
]


@dataclass
class TaxonomyConstraints:
    category: str | None
    subcategory: str | None
    use_cases: list[str]
    preferences: list[str]
    strict_filter: bool


@lru_cache
def load_taxonomy() -> dict[str, Any]:
    with TAXONOMY_PATH.open("r", encoding="utf-8") as file:
        return json.load(file)


def extract_taxonomy_constraints(text: str, *, budget: int | None = None) -> TaxonomyConstraints:
    category, subcategory = match_subcategory(text)
    category = category or match_category(text)
    use_cases = extract_taxonomy_values(text, value_type="use_cases")
    preferences = extract_taxonomy_values(text, value_type="preferences")
    if budget is not None and "性价比" not in preferences:
        preferences.append("性价比")
    return TaxonomyConstraints(
        category=category,
        subcategory=subcategory,
        use_cases=use_cases,
        preferences=preferences,
        strict_filter=is_strict_filter_query(text, budget=budget),
    )


def match_category(text: str) -> str | None:
    lowered = text.lower()
    best: tuple[int, str] | None = None
    for category in load_taxonomy().get("categories", []):
        for alias in [category["name"], *category.get("aliases", [])]:
            normalized = alias.lower()
            if normalized in lowered:
                candidate = (len(normalized), category["name"])
                if best is None or candidate[0] > best[0]:
                    best = candidate
    return best[1] if best else None


def match_subcategory(text: str) -> tuple[str | None, str | None]:
    lowered = text.lower()
    best: tuple[int, str, str] | None = None
    for category in load_taxonomy().get("categories", []):
        for subcategory in category.get("subcategories", []):
            for alias in [subcategory["name"], *subcategory.get("aliases", [])]:
                normalized = alias.lower()
                if normalized in lowered:
                    candidate = (len(normalized), category["name"], subcategory["name"])
                    if best is None or candidate[0] > best[0]:
                        best = candidate
    if best is None:
        return None, None
    return best[1], best[2]


def extract_taxonomy_values(text: str, *, value_type: str) -> list[str]:
    lowered = text.lower()
    values: list[str] = []
    for category in load_taxonomy().get("categories", []):
        attributes = category.get("attributes", {}).get(value_type, {})
        for value, aliases in attributes.items():
            if any(alias.lower() in lowered for alias in aliases):
                values.append(value)
    return list(dict.fromkeys(values))


def is_strict_filter_query(text: str, *, budget: int | None = None) -> bool:
    if budget is None:
        return False
    lowered = text.lower()
    return any(keyword in lowered for keyword in STRICT_FILTER_KEYWORDS)


def product_matches_subcategory(product: Product, subcategory: str) -> bool:
    inferred = infer_product_subcategory(product)
    if inferred:
        return inferred == subcategory
    aliases = get_subcategory_aliases(subcategory)
    haystack = _product_identity_text(product)
    return any(alias.lower() in haystack for alias in aliases)


def infer_product_subcategory(product: Product) -> str | None:
    haystack = _product_identity_text(product)
    best: tuple[int, str] | None = None
    for category in load_taxonomy().get("categories", []):
        if product.category and product.category != category["name"]:
            continue
        for subcategory in category.get("subcategories", []):
            for alias in [subcategory["name"], *subcategory.get("aliases", [])]:
                normalized = alias.lower()
                if normalized in haystack:
                    candidate = (len(normalized), subcategory["name"])
                    if best is None or candidate[0] > best[0]:
                        best = candidate
    return best[1] if best else None


def get_subcategory_aliases(subcategory_name: str) -> list[str]:
    for category in load_taxonomy().get("categories", []):
        for subcategory in category.get("subcategories", []):
            if subcategory["name"] == subcategory_name:
                return [subcategory["name"], *subcategory.get("aliases", [])]
    return [subcategory_name]


def _product_identity_text(product: Product) -> str:
    return " ".join([product.title, product.brand]).lower()
