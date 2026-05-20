from sqlalchemy.orm import Session

from app.agents.intent_router import extract_shopping_constraints
from app.agents.shopping_guide import product_to_card
from app.models.tables import Product
from app.retrieval.image_index import ImageIndex
from app.retrieval.reranker import rerank_image_candidates


def run_multimodal_search(
    db: Session,
    *,
    query: str,
    image_path: str,
    chroma_path: str | None = None,
) -> dict:
    constraints = extract_shopping_constraints(query).model_dump()
    image_index = ImageIndex(chroma_path=chroma_path)
    image_index.index_product_images(db)
    image_candidates = image_index.search_by_image(image_path, limit=12)
    ranked = rerank_image_candidates(
        image_candidates,
        text_query=query,
        budget_max=constraints.get("budget_max"),
        category=constraints.get("category"),
    )
    products = _load_products(db, [item["product_id"] for item in ranked[:3]])
    product_by_id = {product.id: product for product in products}
    cards = []
    for item in ranked[:3]:
        product = product_by_id.get(item["product_id"])
        if not product:
            continue
        card = product_to_card(product, constraints, len(cards) + 1)
        card["score"] = item["final_score"]
        card["reasons"] = _multimodal_reasons(product, constraints)
        cards.append(card)
    return {
        "intent": "multimodal_search",
        "constraints": constraints,
        "memory": constraints,
        "retrieved_items": ranked[:5],
        "product_cards": cards,
        "answer": "我先按图片外观找相似商品，再结合你的价格和场景约束做了筛选。",
        "trace": [
            {
                "node": "multimodal_search",
                "image_candidates": [item["metadata"]["product_id"] for item in image_candidates],
                "final_scores": [
                    {"product_id": item["product_id"], "score": item["final_score"]}
                    for item in ranked[:5]
                ],
            }
        ],
    }


def _load_products(db: Session, product_ids: list[str]) -> list[Product]:
    if not product_ids:
        return []
    return db.query(Product).filter(Product.id.in_(product_ids)).all()


def _multimodal_reasons(product: Product, constraints: dict) -> list[str]:
    reasons = ["外观相似"]
    budget = constraints.get("budget_max")
    if budget and product.price <= budget:
        reasons.append("价格符合")
    for use_case in constraints.get("use_cases", []):
        reasons.append(f"适合{use_case}")
    return reasons[:3]
