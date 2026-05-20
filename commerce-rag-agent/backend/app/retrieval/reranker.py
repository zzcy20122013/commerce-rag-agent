def rerank_image_candidates(
    candidates: list[dict],
    *,
    text_query: str = "",
    budget_max: int | None = None,
    category: str | None = None,
) -> list[dict]:
    filtered = []
    max_sales = max((item["metadata"].get("sales", 0) for item in candidates), default=1) or 1
    for item in candidates:
        metadata = item["metadata"]
        price = metadata.get("price", 0)
        stock = metadata.get("stock", 0)
        if category and metadata.get("category") != category:
            continue
        if budget_max is not None and price > budget_max:
            continue
        if stock <= 0:
            continue
        image_similarity = float(item.get("image_similarity", 0))
        text_similarity = _text_similarity(text_query, metadata)
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


def _text_similarity(text_query: str, metadata: dict) -> float:
    if not text_query:
        return 0.0
    haystack = " ".join(str(metadata.get(key, "")) for key in ["category", "brand"])
    hits = sum(1 for char in set(text_query) if char and char in haystack)
    return min(hits / max(len(set(text_query)), 1), 1.0)
