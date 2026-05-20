from sqlalchemy.orm import Session

from app.agents.intent_router import extract_shopping_constraints
from app.llm.generation import generate_shopping_answer
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
        products = sort_products_for_memory(products, memory)
        cards = [product_to_card(product, memory, rank) for rank, product in enumerate(products[:3], start=1)]
        fallback_answer = build_recommendation_answer(cards, memory)
        answer = generate_shopping_answer(
            query=query,
            cards=cards,
            memory=memory,
            fallback=fallback_answer,
        )
        return {
            **state,
            "constraints": constraints,
            "memory": {**memory, "last_product_ids": [product.id for product in products[:3]]},
            "retrieved_items": [{"product_id": product.id, "title": product.title} for product in products[:5]],
            "product_cards": cards,
            "answer": answer,
            "trace": state.get("trace", []) + [
                {
                    "node": "shopping_guide",
                    "cards": [card["product_id"] for card in cards],
                    "llm_enabled": answer != fallback_answer,
                }
            ],
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
    return memory


def sort_products_for_memory(products: list[Product], memory: dict) -> list[Product]:
    preferences = set(memory.get("preferences", []))
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
