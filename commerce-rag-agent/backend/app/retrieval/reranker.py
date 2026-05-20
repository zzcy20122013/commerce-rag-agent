def rerank_image_candidates(
    candidates: list[dict],
    *,
    text_query: str = "",
    budget_max: int | None = None,
    category: str | None = None,
    visual_terms: list[str] | None = None,
) -> list[dict]:
    filtered = []
    max_sales = max((item["metadata"].get("sales", 0) for item in candidates), default=1) or 1
    for item in candidates:
        metadata = item["metadata"]
        price = metadata.get("price", 0)
        stock = metadata.get("stock", 0)
        if category and metadata.get("category") != category:
            continue
        if visual_terms and not _contains_visual_term(item, visual_terms):
            continue
        if budget_max is not None and price > budget_max:
            continue
        if stock <= 0:
            continue
        image_similarity = float(item.get("image_similarity", 0))
        text_similarity = _text_similarity(text_query, item)
        rating_score = min(float(metadata.get("rating", 0)) / 5.0, 1.0)
        sales_score = min(float(metadata.get("sales", 0)) / max_sales, 1.0)
        stock_score = min(float(stock) / 100.0, 1.0)
        final_score = (
            image_similarity * 0.45
            + text_similarity * 0.25
            + rating_score * 0.10
            + sales_score * 0.10
            + stock_score * 0.10
        )
        filtered.append(
            {
                **item,
                "product_id": metadata["product_id"],
                "final_score": round(final_score, 4),
            }
        )
    return sorted(filtered, key=lambda item: item["final_score"], reverse=True)


def _contains_visual_term(item: dict, visual_terms: list[str]) -> bool:
    haystack = _candidate_text(item)
    return any(term in haystack for term in visual_terms)


def _text_similarity(text_query: str, item: dict) -> float:
    if not text_query:
        return 0.0
    haystack = _candidate_text(item)
    keyword_hits = sum(1 for keyword in _query_keywords(text_query) if keyword in haystack)
    char_hits = sum(1 for char in set(text_query) if char.strip() and char in haystack)
    keyword_score = keyword_hits / max(len(_query_keywords(text_query)), 1)
    char_score = char_hits / max(len(set(text_query)), 1)
    return min(keyword_score * 0.7 + char_score * 0.3, 1.0)


def _candidate_text(item: dict) -> str:
    metadata = item.get("metadata", {})
    return " ".join(
        str(value)
        for value in [
            item.get("text", ""),
            metadata.get("category", ""),
            metadata.get("brand", ""),
            metadata.get("title", ""),
        ]
    )


def _query_keywords(text_query: str) -> list[str]:
    keywords = [
        "通勤",
        "跑步",
        "训练",
        "户外",
        "学生",
        "轻便",
        "舒适",
        "鞋",
        "跑鞋",
        "篮球鞋",
        "徒步鞋",
        "背包",
        "帽",
        "T恤",
        "短袖",
        "裤",
        "平板",
        "耳机",
        "精华",
        "敏感肌",
        "修护",
    ]
    return [keyword for keyword in keywords if keyword.lower() in text_query.lower()]
