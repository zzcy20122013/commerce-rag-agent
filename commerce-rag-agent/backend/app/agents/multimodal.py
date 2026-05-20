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
    image_index.ensure_product_images_indexed(db)
    image_candidates = image_index.search_by_image(image_path, limit=24)
    visual_terms = infer_visual_terms(image_candidates)
    ranked = rerank_image_candidates(
        image_candidates,
        text_query=query,
        budget_max=constraints.get("budget_max"),
        category=constraints.get("category"),
        visual_terms=visual_terms,
    )
    relaxed_budget = False
    relaxed_visual_terms = False
    if not ranked and constraints.get("budget_max") is not None:
        ranked = rerank_image_candidates(
            image_candidates,
            text_query=query,
            budget_max=None,
            category=constraints.get("category"),
            visual_terms=visual_terms,
        )
        relaxed_budget = bool(ranked)
    if not ranked and visual_terms:
        ranked = rerank_image_candidates(
            image_candidates,
            text_query=query,
            budget_max=constraints.get("budget_max"),
            category=constraints.get("category"),
            visual_terms=None,
        )
        relaxed_visual_terms = bool(ranked)
    products = _load_products(db, [item["product_id"] for item in ranked[:3]])
    product_by_id = {product.id: product for product in products}
    cards = []
    for item in ranked[:3]:
        product = product_by_id.get(item["product_id"])
        if not product:
            continue
        card = product_to_card(product, constraints, len(cards) + 1)
        card["score"] = item["final_score"]
        card["reasons"] = _multimodal_reasons(product, constraints, relaxed_visual_terms=relaxed_visual_terms)
        cards.append(card)
    return {
        "intent": "multimodal_search",
        "constraints": constraints,
        "memory": constraints,
        "retrieved_items": ranked[:5],
        "product_cards": cards,
        "answer": build_multimodal_answer(
            cards,
            constraints,
            visual_terms=visual_terms,
            relaxed_budget=relaxed_budget,
            relaxed_visual_terms=relaxed_visual_terms,
        ),
        "trace": [
            {
                "node": "multimodal_search",
                "visual_terms": visual_terms,
                "relaxed_budget": relaxed_budget,
                "relaxed_visual_terms": relaxed_visual_terms,
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


def _multimodal_reasons(
    product: Product,
    constraints: dict,
    *,
    relaxed_visual_terms: bool = False,
) -> list[str]:
    reasons = ["外观相似"]
    if relaxed_visual_terms:
        reasons = ["文本约束匹配"]
    budget = constraints.get("budget_max")
    if budget and product.price <= budget:
        reasons.append("价格符合")
    elif budget:
        reasons.append("超出预算")
    for use_case in constraints.get("use_cases", []):
        reasons.append(f"适合{use_case}")
    return reasons[:3]


VISUAL_TERM_GROUPS = [
    ["篮球鞋", "跑鞋", "徒步鞋", "鞋"],
    ["双肩背包", "背包", "包"],
    ["棒球帽", "鸭舌帽", "帽"],
    ["T恤", "短袖"],
    ["长裤", "短裤", "裤"],
    ["卫衣"],
    ["平板"],
    ["耳机"],
    ["精华"],
    ["面霜"],
    ["咖啡"],
]


def infer_visual_terms(candidates: list[dict]) -> list[str]:
    if not candidates:
        return []
    top_text = " ".join(_candidate_text(item) for item in candidates[:3])
    for group in VISUAL_TERM_GROUPS:
        if any(term in top_text for term in group):
            return group
    return []


def build_multimodal_answer(
    cards: list[dict],
    constraints: dict,
    *,
    visual_terms: list[str],
    relaxed_budget: bool,
    relaxed_visual_terms: bool,
) -> str:
    if not cards:
        return "我按图片外观和文字条件检索了商品，但暂时没有找到足够匹配的结果，可以放宽预算或换一张更清晰的图片再试。"
    if relaxed_budget:
        budget = constraints.get("budget_max")
        visual_name = visual_terms[-1] if visual_terms else "相似款"
        return (
            f"我按图片外观判断更接近{visual_name}，但当前商品库里没有找到 {budget} 元以内的高相似商品。"
            "下面先给你相似度更高的选择，并在卡片里标出预算情况。"
        )
    if relaxed_visual_terms:
        return "我按价格和场景约束找到了商品，但图片外观相似度会弱一些，下面结果更偏文字条件匹配。"
    return "我先按图片外观找相似商品，再结合你的价格和场景约束做了筛选。"


def _candidate_text(item: dict) -> str:
    metadata = item.get("metadata", {})
    return " ".join(
        str(value)
        for value in [
            item.get("text", ""),
            metadata.get("title", ""),
            metadata.get("category", ""),
            metadata.get("brand", ""),
        ]
    )
