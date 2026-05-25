from sqlalchemy.orm import Session

from app.agents.intent_router import extract_shopping_constraints
from app.agents.shopping_guide import (
    build_generation_memory,
    build_recommendation_answer,
    hybrid_retrieve_and_rerank,
    merge_memory,
    product_to_card,
)
from app.llm.generation import generate_decision_guide_result
from app.services.product_service import filter_products


def decision_guide_node(db: Session):
    def node(state: dict) -> dict:
        query = state["query"]
        constraints = extract_shopping_constraints(query).model_dump()
        memory = merge_memory(state.get("memory", {}), constraints, query)
        products = filter_products(
            db,
            category=memory.get("category"),
            subcategory=memory.get("subcategory"),
            budget_max=memory.get("budget_max"),
        )
        products, retrieval_trace = hybrid_retrieve_and_rerank(db, products, memory, query)
        cards = [product_to_card(product, memory, rank) for rank, product in enumerate(products[:3], start=1)]
        fallback_answer = build_decision_fallback(cards, memory)
        generation_memory = build_generation_memory(memory, cards, no_exact_match=False)
        generation_memory["decision_mode"] = "open_ended_purchase"
        generation_memory["answer_policy"] = (
            "先帮助用户理解怎么选，再结合商品库推荐；如果专业、预算、是否游戏等信息不足，结尾主动追问。"
        )
        generation = generate_decision_guide_result(
            query=query,
            cards=cards,
            memory=generation_memory,
            fallback=fallback_answer,
        )
        trace_item = {
            "node": "decision_guide",
            "cards": [card["product_id"] for card in cards],
            "llm_enabled": generation.llm_enabled,
            **retrieval_trace,
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


def build_decision_fallback(cards: list[dict], memory: dict) -> str:
    subcategory = memory.get("subcategory") or memory.get("category") or "商品"
    if not cards:
        return f"先别急着下单，买{subcategory}我建议先确认预算、主要用途和品牌生态，我再按这些条件帮你缩小范围。"
    first = cards[0]
    second = cards[1] if len(cards) > 1 else None
    if subcategory == "笔记本电脑":
        compare_text = ""
        if second:
            compare_text = f"如果你更看重品牌生态或价格，也可以对比 {second['title']}，价格约 {second['price']} 元。"
        return (
            "先按用途分会更稳：如果只是上课、写论文、网课，轻薄本就够；"
            "如果是计算机、设计、剪视频或 3D 游戏，就要更看重处理器、内存和显卡。"
            "预算上，普通大学日常一般看 5000-7000 元档；游戏或重度创作通常要再往上加。\n\n"
            "核心参数我建议这样看：内存至少 16GB，想多开软件或长期用尽量 32GB；"
            "硬盘 512GB 起步，资料和项目多就看 1TB；屏幕优先 14-16 英寸、高分辨率，带去上课也别太重。\n\n"
            f"结合现在可选商品，您可以优先看 {first['title']}，价格约 {first['price']} 元。"
            f"{compare_text}"
            "你再补充一下预算上限、专业方向、会不会打大型游戏，我就能继续帮你缩到一两款。"
        )
    return (
        f"买{subcategory}可以先看用途、预算和长期使用成本。"
        f"如果先给一个方向，您可以优先看 {first['title']}，价格约 {first['price']} 元。"
        "你再告诉我预算和主要用途，我可以继续帮你缩到一两款。"
    )
