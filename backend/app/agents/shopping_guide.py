import json

from sqlalchemy.orm import Session

from app.agents.intent_router import extract_shopping_constraints
from app.llm.generation import generate_shopping_result
from app.models.tables import Product
from app.retrieval.text_index import TextIndex
from app.services.product_service import filter_products


MEMORY_FIELDS = [
    "budget_max",
    "category",
    "subcategory",
    "audience",
    "use_cases",
    "preferences",
    "product_ids",
    "strict_filter",
    "last_product_ids",
    "exclude_product_ids",
]


def shopping_guide_node(db: Session):
    def node(state: dict) -> dict:
        query = state["query"]
        constraints = extract_shopping_constraints(query).model_dump()
        memory = merge_memory(state.get("memory", {}), constraints, query)
        effective_constraints = build_effective_constraints(constraints, memory)
        products = filter_products(
            db,
            category=memory.get("category"),
            subcategory=memory.get("subcategory"),
            budget_max=memory.get("budget_max"),
        )
        alternative_products = exclude_previous_products(products, memory)
        if memory.get("exclude_product_ids") and not alternative_products:
            cards: list[dict] = []
            answer = build_no_more_options_answer(memory)
            trace_item = {
                "node": "shopping_guide",
                "cards": [],
                "llm_enabled": False,
                "retrieval_mode": "sqlite_filter_no_new_alternatives",
                "sqlite_candidates": len(products),
                "excluded_product_ids": memory.get("exclude_product_ids", []),
            }
            return {
                **state,
                "constraints": effective_constraints,
                "memory": {**memory, "exclude_product_ids": []},
                "retrieved_items": [],
                "product_cards": cards,
                "no_exact_match": False,
                "answer": answer,
                "trace": state.get("trace", []) + [trace_item],
            }
        products = alternative_products
        if not products and memory.get("strict_filter"):
            cards: list[dict] = []
            answer = build_recommendation_answer(cards, memory, strict_no_match=True)
            trace_item = {
                "node": "shopping_guide",
                "cards": [],
                "llm_enabled": False,
                "retrieval_mode": "sqlite_strict_filter_empty",
                "sqlite_candidates": 0,
                "chroma_hits": [],
                "fallback_reason": "strict_filter_no_match",
            }
            return {
                **state,
                "constraints": effective_constraints,
                "memory": {**memory, "last_product_ids": []},
                "retrieved_items": [],
                "product_cards": cards,
                "no_exact_match": True,
                "answer": answer,
                "trace": state.get("trace", []) + [trace_item],
            }
        no_exact_match = False
        if not products and memory.get("subcategory") and memory.get("budget_max"):
            no_exact_match = True
            products = filter_products(
                db,
                category=memory.get("category"),
                subcategory=memory.get("subcategory"),
                budget_max=None,
            )
        products, retrieval_trace = hybrid_retrieve_and_rerank(db, products, memory, query)
        cards = [product_to_card(product, memory, rank) for rank, product in enumerate(products[:3], start=1)]
        fallback_answer = build_recommendation_answer(cards, memory, no_exact_match=no_exact_match)
        generation_memory = build_generation_memory(memory, cards, no_exact_match=no_exact_match)
        generation = generate_shopping_result(
            query=query,
            cards=cards,
            memory=generation_memory,
            fallback=fallback_answer,
        )
        answer = generation.content
        trace_item = {
            "node": "shopping_guide",
            "cards": [card["product_id"] for card in cards],
            "llm_enabled": generation.llm_enabled,
            **retrieval_trace,
        }
        if no_exact_match:
            trace_item["fallback_reason"] = "no_exact_subcategory_budget_match"
        if generation.llm_error:
            trace_item["llm_error"] = generation.llm_error
        return {
            **state,
            "constraints": effective_constraints,
            "memory": {**memory, "last_product_ids": [product.id for product in products[:3]]},
            "retrieved_items": [{"product_id": product.id, "title": product.title} for product in products[:5]],
            "product_cards": cards,
            "no_exact_match": no_exact_match,
            "answer": answer,
            "trace": state.get("trace", []) + [trace_item],
        }

    return node


def merge_memory(previous: dict, constraints: dict, query: str) -> dict:
    memory = {field: previous.get(field) for field in MEMORY_FIELDS if field in previous}
    for field in MEMORY_FIELDS:
        value = constraints.get(field)
        if value:
            if isinstance(value, list):
                merged = list(dict.fromkeys(memory.get(field, []) + value))
                memory[field] = merged
            else:
                memory[field] = value
    memory["strict_filter"] = bool(constraints.get("strict_filter") or previous.get("strict_filter"))
    if constraints.get("category") and not constraints.get("subcategory") and _asks_for_broad_category(query):
        memory.pop("subcategory", None)
    lowered = query.lower()
    if any(word in lowered for word in ["更轻", "轻一点", "轻便", "portable"]):
        _append_preference(memory, "轻便")
    if any(word in lowered for word in ["便宜", "省钱", "划算", "cheaper"]):
        _append_preference(memory, "性价比")
    if any(word in lowered for word in ["敏感肌", "易敏肌", "温和", "无刺激"]):
        _append_preference(memory, "敏感肌友好")
    if any(word in lowered for word in ["修护", "维稳", "屏障"]):
        _append_preference(memory, "修护维稳")
    if any(word in lowered for word in ["保湿", "补水"]):
        _append_preference(memory, "保湿")
    for color, aliases in COLOR_PREFERENCE_ALIASES.items():
        if any(alias in lowered for alias in aliases):
            _append_preference(memory, color)
    if _asks_for_more_options(query):
        memory["exclude_product_ids"] = previous.get("last_product_ids", [])
    else:
        memory.pop("exclude_product_ids", None)
    return memory


def build_effective_constraints(constraints: dict, memory: dict) -> dict:
    effective = dict(constraints)
    for field in [
        "category",
        "subcategory",
        "budget_max",
        "audience",
        "use_cases",
        "preferences",
        "product_ids",
        "strict_filter",
    ]:
        if memory.get(field):
            effective[field] = memory[field]
    return effective


def exclude_previous_products(products: list[Product], memory: dict) -> list[Product]:
    excluded = set(memory.get("exclude_product_ids") or [])
    if not excluded:
        return products
    return [product for product in products if product.id not in excluded]


def sort_products_for_memory(products: list[Product], memory: dict, query: str = "") -> list[Product]:
    preferences = set(memory.get("preferences", []))
    ranked = [(_score_product(product, memory, query), product) for product in products]
    if any(score > 0 for score, _ in ranked):
        return [
            product
            for _, product in sorted(
                ranked,
                key=lambda item: (
                    -item[0],
                    item[1].price if "性价比" in preferences else 0,
                    -item[1].rating,
                    -item[1].sales,
                ),
            )
        ]
    if "轻便" in preferences:
        return sorted(products, key=lambda product: (product.price, -product.rating))
    if "性价比" in preferences:
        return sorted(products, key=lambda product: (product.price, -product.sales))
    return products


def hybrid_retrieve_and_rerank(
    db: Session,
    candidates: list[Product],
    memory: dict,
    query: str,
) -> tuple[list[Product], dict]:
    if not candidates:
        return [], {"retrieval_mode": "sqlite_filter_empty", "sqlite_candidates": 0, "chroma_hits": []}

    candidate_by_id = {product.id: product for product in candidates}
    query_text = build_retrieval_query(query, memory)
    try:
        index = TextIndex()
        index.ensure_products_indexed(db)
        hits = index.search_products(
            query_text,
            limit=min(max(len(candidates), 10), 30),
            product_ids=list(candidate_by_id),
        )
    except Exception as error:
        return sort_products_for_memory(candidates, memory, query), {
            "retrieval_mode": "sqlite_filter_local_rerank",
            "sqlite_candidates": len(candidates),
            "chroma_hits": [],
            "chroma_error": f"{type(error).__name__}: {str(error)[:160]}",
        }

    semantic_scores = {
        hit["metadata"]["product_id"]: _semantic_score(hit.get("distance"))
        for hit in hits
        if hit.get("metadata", {}).get("product_id") in candidate_by_id
    }
    ranked = sorted(
        candidates,
        key=lambda product: (
            -_hybrid_score(product, memory, query, semantic_scores),
            product.price if "性价比" in set(memory.get("preferences", [])) else 0,
            -product.rating,
            -product.sales,
        ),
    )
    return ranked, {
        "retrieval_mode": "sqlite_filter_chroma_rerank",
        "sqlite_candidates": len(candidates),
        "chroma_hits": [hit["metadata"]["product_id"] for hit in hits[:5] if hit.get("metadata")],
    }


def build_retrieval_query(query: str, memory: dict) -> str:
    parts = [
        query,
        memory.get("category") or "",
        memory.get("subcategory") or "",
        memory.get("audience") or "",
        " ".join(memory.get("use_cases", [])),
        " ".join(memory.get("preferences", [])),
    ]
    if memory.get("budget_max"):
        parts.append(f"{memory['budget_max']} 元以内")
    return " ".join(part for part in parts if part).strip()


def build_generation_memory(memory: dict, cards: list[dict], *, no_exact_match: bool) -> dict:
    generation_memory = dict(memory)
    generation_memory["no_exact_match"] = no_exact_match
    if no_exact_match:
        budget = memory.get("budget_max")
        candidate_prices = [card["price"] for card in cards]
        lowest_price = min(candidate_prices) if candidate_prices else None
        gap = lowest_price - budget if budget and lowest_price else None
        generation_memory["answer_policy"] = (
            "没有严格符合预算和子品类的商品；不能把超预算备选说成预算内推荐。"
            "请先明确说明没有精确匹配，再解释为什么展示这些同子品类备选，"
            "给出预算差距、是否值得加预算、以及如果预算不变可以怎么调整需求。"
            "不要推荐候选卡片之外的具体商品。"
        )
        generation_memory["budget_gap_min"] = gap
        generation_memory["lowest_candidate_price"] = lowest_price
    return generation_memory


def _semantic_score(distance: float | None) -> float:
    if distance is None:
        return 0.0
    return 1.0 / (1.0 + max(float(distance), 0.0))


def _hybrid_score(product: Product, memory: dict, query: str, semantic_scores: dict[str, float]) -> float:
    semantic = semantic_scores.get(product.id, 0.0)
    local = _score_product(product, memory, query)
    return semantic * 20 + local


def product_to_card(product: Product, memory: dict, rank: int) -> dict:
    reasons = []
    if memory.get("budget_max") and product.price <= memory["budget_max"]:
        reasons.append(f"预算内：{product.price}<={memory['budget_max']}")
    elif memory.get("budget_max") and product.price > memory["budget_max"]:
        reasons.append(f"超预算：{product.price}>{memory['budget_max']}")
    product_text = _product_explain_text(product)
    for use_case in memory.get("use_cases", []):
        if use_case.lower() in product_text:
            reasons.append(f"适合{use_case}")
    for preference in memory.get("preferences", []):
        if preference.lower() in product_text:
            reasons.append(f"命中偏好：{preference}")
    if product.rating >= 4.5:
        reasons.append(f"评分较高：{product.rating:.1f}")
    if product.sales >= 1000:
        reasons.append(f"销量较高：{product.sales}")
    risk_text = format_review_risk_reason(product)
    if risk_text:
        reasons.append(risk_text)
    if memory.get("subcategory") and not any("适合" in reason or "命中偏好" in reason for reason in reasons):
        reasons.append(f"品类匹配：{memory['subcategory']}")
    if not reasons:
        reasons.append("综合评分靠前")
    return {
        "product_id": product.id,
        "title": product.title,
        "subtitle": product.description,
        "price": product.price,
        "original_price": product.price,
        "image_url": product.image_url,
        "rating": product.rating,
        "sales": product.sales,
        "stock_status": "in_stock" if product.stock > 0 else "out_of_stock",
        "reasons": list(dict.fromkeys(reasons))[:6],
        "score": round(max(0.5, 0.95 - rank * 0.04), 2),
    }


def build_recommendation_answer(
    cards: list[dict],
    memory: dict,
    *,
    no_exact_match: bool = False,
    strict_no_match: bool = False,
) -> str:
    if not cards:
        if strict_no_match:
            category = memory.get("subcategory") or memory.get("category") or "商品"
            budget = f"{memory['budget_max']} 元以内" if memory.get("budget_max") else "当前条件"
            return (
                f"我这边没有找到严格符合“{budget}、{category}”的现货商品。"
                "更建议你先别硬买超预算或不相关的款，容易花了钱还不合适。"
                "如果预算卡死，可以换成相邻品类再查；如果能调整预算，我建议先把预算放宽一点再选。"
            )
        return "我暂时没有找到完全符合条件的商品，可以放宽预算或换一个品类再试。"
    category = memory.get("category") or "商品"
    subcategory = memory.get("subcategory") or ""
    budget = f"{memory['budget_max']} 元以内" if memory.get("budget_max") else ""
    if no_exact_match:
        prices = [card["price"] for card in cards]
        lowest_price = min(prices) if prices else None
        gap_text = ""
        if lowest_price and memory.get("budget_max"):
            gap_text = f"我看到最接近的一款也要 {lowest_price} 元，比你的预算高 {lowest_price - memory['budget_max']} 元。"
        return (
            f"你这个预算卡得比较紧，我暂时没找到严格符合 {budget}{subcategory or category} 的选择。"
            f"{gap_text}"
            "下面这些只能算同类里的加预算备选；如果预算不能提高，我更建议你放宽品牌、屏幕尺寸，或者等活动价/看二手。"
        )
    top_card = cards[0]
    top_reason_text = format_card_reasons(top_card)
    if len(cards) == 1:
        return (
            f"我会先看这款：{top_card['title']}，价格是 {top_card['price']} 元。"
            f"{f'主推理由是{top_reason_text}。' if top_reason_text else ''}"
            "如果你想更稳一点，可以再补充预算、品牌偏好或不能接受的点，我再帮你缩小范围。"
        )
    second_card = cards[1]
    second_reason_text = format_card_reasons(second_card, limit=2)
    return (
        f"这几款里我会优先看 {top_card['title']}，价格 {top_card['price']} 元，"
        f"{f'主推理由是{top_reason_text}。' if top_reason_text else '整体更贴近你的需求。'}"
        f"如果你想留个备选，可以再看看 {second_card['title']}，它是 {second_card['price']} 元"
        f"{f'，主要优势是{second_reason_text}' if second_reason_text else ''}。"
        "我建议你先按预算和最在意的使用场景二选一，不用只盯参数。"
    )


def format_card_reasons(card: dict, *, limit: int = 3) -> str:
    reasons = [str(reason) for reason in card.get("reasons", []) if str(reason).strip()]
    return "、".join(reasons[:limit])


def _product_explain_text(product: Product) -> str:
    return " ".join(
        [
            product.title,
            product.category,
            product.brand,
            product.description,
            product.specs_json or "",
        ]
    ).lower()


def format_review_risk_reason(product: Product) -> str:
    summary = _safe_product_specs(product).get("review_summary") or {}
    count = int(summary.get("negative_review_count") or 0)
    keywords = [str(keyword) for keyword in summary.get("negative_keywords") or [] if str(keyword).strip()]
    if count <= 0 or not keywords:
        return ""
    return f"差评提醒：{('/'.join(keywords[:2]))}反馈"


def build_no_more_options_answer(memory: dict) -> str:
    category = memory.get("subcategory") or memory.get("category") or "这个品类"
    budget = f"{memory['budget_max']} 元以内" if memory.get("budget_max") else "当前条件下"
    focus_items = [*memory.get("use_cases", []), *memory.get("preferences", [])]
    focus = "、".join(focus_items[:2]) if focus_items else "你的核心需求"
    return (
        f"我又帮你往下找了一圈，{budget}适合你的{category}选择确实不多。"
        f"刚才给你看的那几款已经算比较稳了，再硬找的话，要么会超预算比较多，要么就不太贴合{focus}。"
        "如果你想继续扩，我建议先放宽一个条件，比如预算、品牌、规格或使用场景。"
    )


def _asks_for_broad_category(query: str) -> bool:
    lowered = query.lower()
    return any(keyword in lowered for keyword in ["都有什么", "有哪些", "电子产品", "数码产品", "全部"])


def _asks_for_more_options(query: str) -> bool:
    lowered = query.lower()
    return any(keyword in lowered for keyword in ["还有", "其他", "别的", "换一批", "换个", "再推荐", "再找"])


def _append_preference(memory: dict, value: str) -> None:
    preferences = memory.get("preferences", [])
    if value not in preferences:
        memory["preferences"] = preferences + [value]


DOMAIN_KEYWORDS = [
    "黑色",
    "白色",
    "灰色",
    "蓝色",
    "红色",
    "粉色",
    "米色",
    "棕色",
    "敏感肌",
    "易敏肌",
    "修护",
    "维稳",
    "屏障",
    "舒缓",
    "保湿",
    "补水",
    "精华",
    "面霜",
    "防晒",
    "控油",
    "抗初老",
    "淡纹",
    "紧致",
    "护肤",
    "美妆",
    "低脂",
    "低糖",
    "早餐",
    "代餐",
    "咖啡",
    "酸奶",
    "通勤",
    "跑步",
    "健身",
    "户外",
    "降噪",
    "续航",
    "轻薄",
    "便携",
    "学生",
    "网课",
    "记笔记",
    "平板",
    "耳机",
    "蓝牙耳机",
    "鞋",
    "跑鞋",
    "板鞋",
    "背包",
    "双肩包",
]


COLOR_PREFERENCE_ALIASES = {
    "黑色": ["黑色", "黑的", "黑款", "黑"],
    "白色": ["白色", "白的", "白款", "白"],
    "灰色": ["灰色", "灰的", "灰款", "灰"],
    "蓝色": ["蓝色", "蓝的", "蓝款", "蓝"],
    "红色": ["红色", "红的", "红款", "红"],
    "粉色": ["粉色", "粉的", "粉款", "粉"],
    "米色": ["米色", "米白", "米"],
    "棕色": ["棕色", "棕", "咖色"],
}


def _score_product(product: Product, memory: dict, query: str) -> float:
    text = " ".join(
        [
            product.title,
            product.category,
            product.brand,
            product.description,
            product.specs_json or "",
        ]
    ).lower()
    score = 0.0

    if memory.get("category") and product.category == memory["category"]:
        score += 8

    for keyword in _query_keywords(query):
        if keyword in text:
            score += 12 if len(keyword) >= 2 else 2

    for use_case in memory.get("use_cases", []):
        normalized = use_case.lower()
        if normalized in text:
            score += 8

    for preference in memory.get("preferences", []):
        normalized = preference.lower()
        if normalized in text:
            score += 6

    if memory.get("budget_max") and product.price <= memory["budget_max"]:
        score += 2

    score -= _review_risk_penalty(product, memory, query)

    score += product.rating * 0.2
    score += min(product.sales, 20000) / 20000
    return score


def _review_risk_penalty(product: Product, memory: dict, query: str) -> float:
    summary = _safe_product_specs(product).get("review_summary") or {}
    count = int(summary.get("negative_review_count") or 0)
    keywords = [str(keyword).lower() for keyword in summary.get("negative_keywords") or [] if str(keyword).strip()]
    if count <= 0 or not keywords:
        return 0.0
    context = " ".join(
        [
            query,
            " ".join(memory.get("preferences", [])),
            " ".join(memory.get("use_cases", [])),
        ]
    ).lower()
    matched = [keyword for keyword in keywords if keyword and keyword in context]
    if not matched:
        return 0.0
    return 14.0 + min(count, 5)


def _safe_product_specs(product: Product) -> dict:
    try:
        parsed = json.loads(product.specs_json or "{}")
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _query_keywords(query: str) -> list[str]:
    lowered = query.lower()
    return [keyword for keyword in DOMAIN_KEYWORDS if keyword in lowered]
