import math
import re
from collections import Counter
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.tables import Product


class KeywordRetrievalService:
    def search(
        self,
        db: Session,
        query: str,
        *,
        memory: dict[str, Any] | None = None,
        candidates: list[Product] | None = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        products = candidates if candidates is not None else list(db.scalars(select(Product).where(Product.stock > 0)).all())
        if not products:
            return []

        terms = _query_terms(query, memory or {})
        if not terms:
            return []

        documents = [_document_tokens(product) for product in products]
        avgdl = sum(len(document) for document in documents) / max(len(documents), 1)
        dfs = _document_frequencies(documents, terms)
        hits: list[dict[str, Any]] = []
        for product, document in zip(products, documents, strict=False):
            score, matched_terms = _bm25_score(document, terms, dfs, len(products), avgdl)
            score += _field_bonus(product, terms)
            score += _memory_bonus(product, memory or {})
            if product.stock <= 0:
                score -= 100
            if score <= 0:
                continue
            hits.append(
                {
                    "product": product,
                    "product_id": product.id,
                    "score": round(score, 4),
                    "matched_terms": matched_terms[:8],
                }
            )
        return sorted(hits, key=lambda item: (-float(item["score"]), item["product"].price))[:limit]


def _query_terms(query: str, memory: dict[str, Any]) -> list[str]:
    parts = [
        query or "",
        str(memory.get("category") or ""),
        str(memory.get("subcategory") or ""),
        str(memory.get("audience") or ""),
        " ".join(_as_list(memory.get("use_cases"))),
        " ".join(_as_list(memory.get("preferences"))),
    ]
    text = " ".join(part for part in parts if part).lower()
    return sorted(set(_tokenize(text, max_terms=120)), key=lambda item: (-len(item), item))[:80]


def _document_tokens(product: Product) -> list[str]:
    text = " ".join(
        [
            product.title,
            product.title,
            product.title,
            product.brand,
            product.brand,
            product.category,
            product.category,
            getattr(product, "subcategory", "") or "",
            getattr(product, "subcategory", "") or "",
            product.description,
            product.specs_json or "",
        ]
    ).lower()
    return _tokenize(text, max_terms=500)


def _tokenize(text: str, *, max_terms: int) -> list[str]:
    tokens: list[str] = []
    tokens.extend(match.group(0) for match in re.finditer(r"[a-z0-9][a-z0-9_\-]{1,31}", text.lower()))
    for chunk in re.findall(r"[\u4e00-\u9fff]{2,}", text.lower()):
        if len(chunk) <= 12:
            tokens.append(chunk)
        for size in (2, 3, 4):
            if len(chunk) >= size:
                tokens.extend(chunk[index : index + size] for index in range(0, len(chunk) - size + 1))
    return [token for token in tokens if len(token) >= 2][:max_terms]


def _document_frequencies(documents: list[list[str]], terms: list[str]) -> dict[str, int]:
    frequencies = {term: 0 for term in terms}
    for document in documents:
        token_set = set(document)
        for term in terms:
            if term in token_set:
                frequencies[term] += 1
    return frequencies


def _bm25_score(
    document: list[str],
    terms: list[str],
    dfs: dict[str, int],
    document_count: int,
    avgdl: float,
) -> tuple[float, list[str]]:
    counts = Counter(document)
    score = 0.0
    matched_terms: list[str] = []
    for term in terms:
        tf = counts.get(term, 0)
        if tf <= 0:
            continue
        df = max(dfs.get(term, 0), 1)
        idf = math.log(1 + (document_count - df + 0.5) / (df + 0.5))
        denominator = tf + 1.5 * (1 - 0.75 + 0.75 * len(document) / max(avgdl, 1.0))
        score += idf * (tf * 2.5) / denominator
        matched_terms.append(term)
    return score, matched_terms


def _field_bonus(product: Product, terms: list[str]) -> float:
    title = (product.title or "").lower()
    brand = (product.brand or "").lower()
    taxonomy = " ".join([product.category or "", getattr(product, "subcategory", "") or ""]).lower()
    detail = " ".join([product.description or "", product.specs_json or ""]).lower()
    score = 0.0
    for term in terms:
        if term in title:
            score += 5.0
        if term in brand:
            score += 2.5
        if term in taxonomy:
            score += 3.0
        if term in detail:
            score += 1.0
    return score


def _memory_bonus(product: Product, memory: dict[str, Any]) -> float:
    score = 0.0
    if memory.get("category") and product.category == memory.get("category"):
        score += 6
    if memory.get("subcategory") and str(memory["subcategory"]) in " ".join(
        [product.title, getattr(product, "subcategory", "") or ""]
    ):
        score += 8
    budget = _to_int(memory.get("budget_max"))
    if budget is not None:
        score += 2 if product.price <= budget else -min((product.price - budget) / max(budget, 1), 4)
    return score


def _as_list(value: Any) -> list[str]:
    if not value:
        return []
    if isinstance(value, list):
        return [str(item) for item in value if item]
    return [str(value)]


def _to_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
