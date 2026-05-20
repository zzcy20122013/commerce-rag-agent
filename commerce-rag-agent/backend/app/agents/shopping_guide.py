from sqlalchemy.orm import Session

from app.agents.intent_router import extract_shopping_constraints
from app.llm.generation import generate_shopping_result
from app.models.tables import Product
from app.services.product_service import filter_products


MEMORY_FIELDS = ["budget_max", "category", "audience", "use_cases", "preferences", "product_ids"]


def shopping_guide_node(db: Session):
    def node(state: dict) -> dict:
        query = state["query"]
        constraints = extract_shopping_constraints(query).model_dump()
        memory = merge_memory(state.get("memory", {}), constraints, query)
        products = filter_products(
            db,
            category=memory.get("category"),
            budget_max=memory.get("budget_max"),
        )
        products = sort_products_for_memory(products, memory, query)
        cards = [product_to_card(product, memory, rank) for rank, product in enumerate(products[:3], start=1)]
        fallback_answer = build_recommendation_answer(cards, memory)
        generation = generate_shopping_result(
            query=query,
            cards=cards,
            memory=memory,
            fallback=fallback_answer,
        )
        trace_item = {
            "node": "shopping_guide",
            "cards": [card["product_id"] for card in cards],
            "llm_enabled": generation.llm_enabled,
        }
        if generation.llm_error:
            trace_item["llm_error"] = generation.llm_error
        return {
            **state,
            "constraints": constraints,
            "memory": {**memory, "last_product_ids": [product.id for product in products[:3]]},
            "retrieved_items": [{"product_id": product.id, "title": product.title} for product in products[:5]],
            "product_cards": cards,
            "answer": generation.content,
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
    return memory


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


def product_to_card(product: Product, memory: dict, rank: int) -> dict:
    reasons = []
    if memory.get("budget_max") and product.price <= memory["budget_max"]:
        reasons.append("预算内")
    for use_case in memory.get("use_cases", []):
        reasons.append(f"适合{use_case}")
    for preference in memory.get("preferences", []):
        reasons.append(preference)
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
        "reasons": list(dict.fromkeys(reasons))[:3],
        "score": round(max(0.5, 0.95 - rank * 0.04), 2),
    }


def build_recommendation_answer(cards: list[dict], memory: dict) -> str:
    if not cards:
        return "我暂时没有找到完全符合条件的商品，可以放宽预算或换一个品类再试。"
    category = memory.get("category") or "商品"
    budget = f"{memory['budget_max']} 元以内" if memory.get("budget_max") else ""
    return f"我按{budget}{category}需求筛选了 {len(cards)} 个更合适的选择，优先考虑预算、用途和库存。"


def _append_preference(memory: dict, value: str) -> None:
    preferences = memory.get("preferences", [])
    if value not in preferences:
        memory["preferences"] = preferences + [value]


DOMAIN_KEYWORDS = [
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

    score += product.rating * 0.2
    score += min(product.sales, 20000) / 20000
    return score


def _query_keywords(query: str) -> list[str]:
    lowered = query.lower()
    return [keyword for keyword in DOMAIN_KEYWORDS if keyword in lowered]
