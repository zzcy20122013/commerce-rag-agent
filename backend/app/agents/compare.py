import json

from sqlalchemy.orm import Session

from app.agents.intent_router import extract_shopping_constraints
from app.agents.shopping_guide import product_to_card
from app.services.product_service import find_products_by_query, get_product_knowledge_docs, get_products_by_ids


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
        docs_by_product = {product.id: get_product_knowledge_docs(db, product.id, limit=3) for product in products}
        comparison = build_comparison_payload(products, query=query, docs_by_product=docs_by_product)
        answer = build_compare_answer(products, query=query, docs_by_product=docs_by_product)
        memory = {**state.get("memory", {}), "last_product_ids": [product.id for product in products]}
        return {
            **state,
            "constraints": constraints,
            "memory": memory,
            "retrieved_items": [{"product_id": product.id, "title": product.title} for product in products],
            "product_cards": cards,
            "comparison": comparison,
            "answer": answer,
            "trace": state.get("trace", []) + [
                {
                    "node": "compare",
                    "products": [product.id for product in products],
                    "doc_hits": {product_id: [doc["id"] for doc in docs] for product_id, docs in docs_by_product.items()},
                }
            ],
        }

    return node


def build_compare_answer(products, *, query: str = "", docs_by_product: dict | None = None) -> str:
    docs_by_product = docs_by_product or {}
    lines = ["我按价格、参数、场景和综合口碑做了对比："]
    for product in products:
        specs = _safe_json(product.specs_json)
        spec_text = "、".join(f"{key}: {value}" for key, value in specs.items()) if specs else "参数较少"
        evidence = _evidence_summary(query, docs_by_product.get(product.id, []))
        lines.append(
            f"- {product.title}：{product.price} 元，评分 {product.rating}，销量 {product.sales}，{spec_text}。{product.description}{evidence}"
        )
    best_match = _best_match_for_query(products, query, docs_by_product)
    cheapest = min(products, key=lambda product: product.price)
    if best_match:
        lines.append(f"结论：如果优先满足你这次提到的需求，我更建议 {best_match.title}。想省钱则优先看 {cheapest.title}。")
    else:
        best_rated = max(products, key=lambda product: product.rating)
        if cheapest.id == best_rated.id:
            lines.append(f"结论：优先选 {cheapest.title}，它同时兼顾价格和评分。")
        else:
            lines.append(f"结论：想省钱选 {cheapest.title}；更看重综合体验选 {best_rated.title}。")
    return "\n".join(lines)


def build_comparison_payload(products, *, query: str = "", docs_by_product: dict | None = None) -> dict:
    docs_by_product = docs_by_product or {}
    keywords = _query_keywords(query)
    best_match = _best_match_for_query(products, query, docs_by_product)
    cheapest = min(products, key=lambda product: product.price) if products else None
    winner = best_match or cheapest
    items = []
    for product in products:
        evidence = _evidence_summary(query, docs_by_product.get(product.id, []))
        matched_keywords = _matched_keywords(product, keywords, docs_by_product.get(product.id, []))
        items.append(
            {
                "product_id": product.id,
                "title": product.title,
                "price": product.price,
                "rating": product.rating,
                "sales": product.sales,
                "stock_status": "in_stock" if product.stock > 0 else "out_of_stock",
                "matched_keywords": matched_keywords,
                "pros": _pros(product, matched_keywords),
                "cons": _cons(product),
                "best_for": _best_for(product, matched_keywords),
                "evidence": evidence.removeprefix(" 证据：") if evidence else "",
                "is_winner": bool(winner and product.id == winner.id),
            }
        )
    return {
        "type": "comparison",
        "title": "商品对比",
        "dimensions": ["价格", "评分", "销量", "需求匹配", "适用建议"],
        "winner_product_id": winner.id if winner else "",
        "winner_reason": _winner_reason(winner, cheapest, keywords) if winner else "",
        "items": items,
    }


def _best_match_for_query(products, query: str, docs_by_product: dict) -> object | None:
    keywords = _query_keywords(query)
    if not keywords:
        return None
    scored = []
    for product in products:
        haystack = " ".join(
            [
                product.title,
                product.description,
                product.specs_json or "",
                " ".join(doc.get("text", "") for doc in docs_by_product.get(product.id, [])),
            ]
        )
        score = sum(1 for keyword in keywords if keyword in haystack)
        scored.append((score, product))
    best_score, best_product = max(scored, key=lambda item: item[0])
    return best_product if best_score > 0 else None


def _evidence_summary(query: str, docs: list[dict]) -> str:
    keywords = _query_keywords(query)
    for doc in docs:
        text = doc.get("text", "")
        if any(keyword in text for keyword in keywords):
            return f" 证据：{text.replace(chr(10), ' ')[:160]}"
    return ""


def _query_keywords(query: str) -> list[str]:
    candidates = ["敏感肌", "修护", "维稳", "保湿", "抗初老", "淡纹", "通勤", "跑步", "低脂", "早餐", "学习", "办公"]
    return [keyword for keyword in candidates if keyword in query]


def _matched_keywords(product, keywords: list[str], docs: list[dict]) -> list[str]:
    haystack = " ".join([product.title, product.description, " ".join(doc.get("text", "") for doc in docs)])
    return [keyword for keyword in keywords if keyword in haystack]


def _pros(product, matched_keywords: list[str]) -> list[str]:
    pros = []
    if matched_keywords:
        pros.append("匹配：" + "、".join(matched_keywords[:3]))
    if product.price:
        pros.append(f"价格 {product.price} 元")
    if product.stock > 0:
        pros.append("有库存")
    if product.sales:
        pros.append(f"销量 {product.sales}")
    return pros[:4]


def _cons(product) -> list[str]:
    cons = []
    if product.rating and product.rating < 3.5:
        cons.append("评分相对一般")
    if product.price > 1000:
        cons.append("价格偏高")
    if product.stock <= 0:
        cons.append("暂无库存")
    return cons or ["暂无明显短板"]


def _best_for(product, matched_keywords: list[str]) -> str:
    if matched_keywords:
        return f"更适合关注{matched_keywords[0]}的人群"
    return f"适合看重{product.category}基础体验的用户"


def _winner_reason(winner, cheapest, keywords: list[str]) -> str:
    if keywords:
        return f"更贴合本次需求：{'、'.join(keywords[:3])}"
    if cheapest and winner.id == cheapest.id:
        return "价格更低，适合作为优先选择"
    return "综合评分和商品信息更占优"


def _safe_json(value: str) -> dict:
    try:
        parsed = json.loads(value or "{}")
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}
