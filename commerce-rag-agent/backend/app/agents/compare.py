import json

from sqlalchemy.orm import Session

from app.agents.intent_router import extract_shopping_constraints
from app.agents.shopping_guide import product_to_card
from app.services.product_service import find_products_by_query, get_products_by_ids


def compare_node(db: Session):
    def node(state: dict) -> dict:
        query = state["query"]
        constraints = extract_shopping_constraints(query).model_dump()
        product_ids = constraints.get("product_ids") or state.get("memory", {}).get("last_product_ids", [])
        products = get_products_by_ids(db, product_ids[:4])
        if len(products) < 2:
            products = find_products_by_query(db, query, limit=4)
        if len(products) < 2:
            return {
                **state,
                "answer": "可以对比，但我需要至少两个明确商品。你可以输入商品 ID，比如：p201 和 p203 哪个更适合学生？",
                "product_cards": [],
                "retrieved_items": [],
                "trace": state.get("trace", []) + [{"node": "compare", "status": "need_two_products"}],
            }

        products = products[:4]
        cards = [product_to_card(product, state.get("memory", {}), rank) for rank, product in enumerate(products, start=1)]
        answer = build_compare_answer(products)
        memory = {**state.get("memory", {}), "last_product_ids": [product.id for product in products]}
        return {
            **state,
            "constraints": constraints,
            "memory": memory,
            "retrieved_items": [{"product_id": product.id, "title": product.title} for product in products],
            "product_cards": cards,
            "answer": answer,
            "trace": state.get("trace", []) + [
                {"node": "compare", "products": [product.id for product in products]}
            ],
        }

    return node


def build_compare_answer(products) -> str:
    lines = ["我按价格、参数、场景和综合口碑做了对比："]
    for product in products:
        specs = _safe_json(product.specs_json)
        spec_text = "、".join(f"{key}: {value}" for key, value in specs.items()) if specs else "参数较少"
        lines.append(
            f"- {product.title}：{product.price} 元，评分 {product.rating}，销量 {product.sales}，{spec_text}。{product.description}"
        )
    cheapest = min(products, key=lambda product: product.price)
    best_rated = max(products, key=lambda product: product.rating)
    if cheapest.id == best_rated.id:
        lines.append(f"结论：优先选 {cheapest.title}，它同时兼顾价格和评分。")
    else:
        lines.append(f"结论：想省钱选 {cheapest.title}；更看重综合体验选 {best_rated.title}。")
    return "\n".join(lines)


def _safe_json(value: str) -> dict:
    try:
        parsed = json.loads(value or "{}")
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}
