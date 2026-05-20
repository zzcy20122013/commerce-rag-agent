import json

from sqlalchemy.orm import Session

from app.agents.shopping_guide import product_to_card
from app.services.product_service import find_products_by_query, get_product_tags


def product_knowledge_node(db: Session):
    def node(state: dict) -> dict:
        query = state["query"]
        products = find_products_by_query(db, query, limit=3)
        if not products:
            return {
                **state,
                "answer": "我还没定位到你问的是哪一款商品，可以补充商品名、商品 ID，或者先让我推荐几款候选。",
                "product_cards": [],
                "retrieved_items": [],
                "trace": state.get("trace", []) + [{"node": "product_knowledge", "status": "need_product"}],
            }

        product = products[0]
        specs = _safe_json(product.specs_json)
        tags = get_product_tags(db, product.id)
        answer = build_product_knowledge_answer(product, specs, tags)
        cards = [product_to_card(item, state.get("memory", {}), rank) for rank, item in enumerate(products, start=1)]
        memory = {**state.get("memory", {}), "last_product_ids": [product.id for product in products]}
        return {
            **state,
            "memory": memory,
            "retrieved_items": [
                {
                    "product_id": product.id,
                    "title": product.title,
                    "source": "products",
                    "metadata": {"specs": specs, "tags": [tag.value for tag in tags]},
                }
            ],
            "product_cards": cards,
            "answer": answer,
            "trace": state.get("trace", []) + [
                {"node": "product_knowledge", "product_id": product.id, "sources": ["products", "product_tags"]}
            ],
        }

    return node


def build_product_knowledge_answer(product, specs: dict, tags: list) -> str:
    spec_text = "、".join(f"{key}: {value}" for key, value in specs.items()) if specs else "暂无结构化参数"
    tag_text = "、".join(tag.value for tag in tags[:6]) if tags else "暂无标签"
    return (
        f"{product.title} 的核心信息如下：价格 {product.price} 元，评分 {product.rating}，库存 {product.stock}。"
        f"商品说明：{product.description} 参数：{spec_text}。相关标签：{tag_text}。"
    )


def _safe_json(value: str) -> dict:
    try:
        parsed = json.loads(value or "{}")
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}
