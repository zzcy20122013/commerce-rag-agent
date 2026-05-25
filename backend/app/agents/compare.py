import json
import re

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
    if _asks_for_difference(query) and len(products) >= 2:
        return build_difference_answer(products[:2], docs_by_product=docs_by_product)
    best_match = _best_match_for_query(products, query, docs_by_product)
    cheapest = min(products, key=lambda product: product.price)
    winner = best_match or cheapest
    keywords = _query_keywords(query)
    focus = "、".join(keywords[:3]) if keywords else "价格、口碑和使用场景"
    lines = [
        f"您主要是在看{focus}，这几款里可以优先看 {winner.title}。"
    ]

    ordered_products = _ordered_compare_products(products, winner, cheapest)
    for product in ordered_products[:3]:
        if product.id == winner.id:
            role = "主推"
        elif product.id == cheapest.id:
            role = "省钱备选"
        else:
            role = "不太建议优先选"
        lines.append(f"{role}：{product.title}，{product.price} 元。{_human_compare_reason(product, query, docs_by_product.get(product.id, []), cheapest)}")

    if cheapest.id != winner.id:
        lines.append(f"如果你更在意少花钱，可以退一步看 {cheapest.title}；但如果重点是{focus}，我还是更建议 {winner.title}。")
    else:
        lines.append(f"我的建议是先看 {winner.title}，它在价格和需求匹配上更稳。")
    return "\n".join(lines)


def build_difference_answer(products, *, docs_by_product: dict | None = None) -> str:
    docs_by_product = docs_by_product or {}
    first, second = products[0], products[1]
    first_points = _difference_points(first, docs_by_product.get(first.id, []))
    second_points = _difference_points(second, docs_by_product.get(second.id, []))
    first_name = _short_product_name(first.title)
    second_name = _short_product_name(second.title)
    shared_price = first.price == second.price
    price_intro = f"价格都在 {first.price} 元" if shared_price else f"价格分别是 {first.price} 元和 {second.price} 元"
    recommendation = _difference_recommendation(first, second, first_points, second_points)
    return (
        f"它们的主要区别在使用侧重点，不是单纯价格差：{price_intro}。"
        f"{first_name} 更偏学习和轻办公稳定性，{_join_points(first_points)}。"
        f"{second_name} 更偏影音、高刷和手机生态联动，{_join_points(second_points)}。"
        f"{recommendation}"
    )


def _ordered_compare_products(products, winner, cheapest):
    ordered = []
    seen = set()
    for product in [winner, cheapest, *products]:
        if product and product.id not in seen:
            ordered.append(product)
            seen.add(product.id)
    return ordered


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
        scored.append((score, product.rating or 0, product.sales or 0, -product.price, product))
    best_score, _, _, _, best_product = max(scored, key=lambda item: item[:4])
    return best_product if best_score > 0 else None


def _evidence_summary(query: str, docs: list[dict]) -> str:
    keywords = _query_keywords(query)
    for doc in docs:
        text = doc.get("text", "")
        if any(keyword in text for keyword in keywords):
            return _clean_evidence_text(text)[:160]
    return ""


def _human_compare_reason(product, query: str, docs: list[dict], cheapest) -> str:
    keywords = _query_keywords(query)
    matched = _matched_keywords(product, keywords, docs)
    points = []
    if matched:
        points.append(f"更贴合你提到的{'、'.join(matched[:2])}")
    if product.id == cheapest.id:
        points.append("价格压力最小")
    if product.rating and product.rating < 3.5:
        points.append("但评分不算突出，建议下单前重点看差评")
    elif product.rating:
        points.append(f"评分 {product.rating}，口碑更稳")
    if not matched and product.description:
        points.append(_short_text(product.description, limit=32))
    return "；".join(points[:3]) + "。"


def _clean_evidence_text(text: str) -> str:
    cleaned = re.sub(r"商品ID：\S+", "", text)
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned.strip()


def _short_text(text: str, *, limit: int) -> str:
    compact = re.sub(r"\s+", " ", text).strip()
    if len(compact) <= limit:
        return compact
    return compact[:limit].rstrip("，。；、 ") + "..."


def _query_keywords(query: str) -> list[str]:
    candidates = ["敏感肌", "修护", "维稳", "保湿", "抗初老", "淡纹", "通勤", "跑步", "低脂", "早餐", "学习", "记笔记", "办公"]
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


def _asks_for_difference(query: str) -> bool:
    return any(keyword in query for keyword in ["区别", "差别", "不同", "差在哪", "哪里不一样"])


def _difference_points(product, docs: list[dict]) -> list[str]:
    text = _product_compare_text(product, docs)
    specs = _safe_json(product.specs_json)
    points: list[str] = []
    sku_text = " ".join(str(item) for item in specs.get("sku_options", []))
    if "5G" in sku_text or "全网通" in sku_text:
        points.append("可选 5G/全网通版本，外出联网更省心")
    elif any(keyword in text for keyword in ["仅支持Wi-Fi", "纯Wi-Fi", "没有插卡", "没有内置插卡", "没法直接插SIM"]):
        points.append("只有 Wi-Fi 版本，外出要靠热点或随身 Wi-Fi")
    if "2.8K" in text or "144Hz" in text:
        values = []
        if "2.8K" in text:
            values.append("2.8K")
        if "144Hz" in text:
            values.append("144Hz 高刷")
        points.append("屏幕卖点更偏" + " + ".join(values))
    if "跨屏互联" in text or "小米生态" in text:
        points.append("和小米手机跨屏互联更方便")
    if "学习模式" in text or "低蓝光" in text:
        points.append("有学习/护眼显示优化")
    if "OTG" in text or "移动硬盘" in text:
        points.append("支持 OTG 外接移动硬盘")
    if "4个应用窗口" in text or "四个APP" in text or "4个窗口" in text:
        points.append("多任务最多可到 4 个窗口")
    if "4096级压感" in text or "2ms" in text:
        points.append("触控笔书写能力描述更具体")
    review_summary = specs.get("review_summary") or {}
    negative_count = int(review_summary.get("negative_review_count") or 0)
    if negative_count > 0:
        points.append(f"评价里有 {negative_count} 条明显负反馈，建议下单前重点看差评")
    if product.sales:
        points.append(f"销量 {product.sales}")
    if product.rating:
        points.append(f"评分 {product.rating:.1f}")
    return list(dict.fromkeys(points))[:5]


def _product_compare_text(product, docs: list[dict]) -> str:
    return " ".join(
        [
            product.title,
            product.description,
            product.specs_json or "",
            " ".join(doc.get("text", "") for doc in docs),
        ]
    )


def _join_points(points: list[str]) -> str:
    return "；".join(points[:4]) if points else "商品库里没有更多可确认的细项参数"


def _difference_recommendation(first, second, first_points: list[str], second_points: list[str]) -> str:
    first_text = " ".join(first_points)
    second_text = " ".join(second_points)
    if "学习" in first_text or "护眼" in first_text or "OTG" in first_text or first.sales >= second.sales:
        return f"如果主要是学生记笔记、网课和轻办公，您可以优先看 {_short_product_name(first.title)}；如果更看重高刷影音或已经在用小米手机，再看 {_short_product_name(second.title)}。"
    return f"如果您更看重高刷影音或生态联动，可以优先看 {_short_product_name(second.title)}；如果更看重学习办公稳定性，再看 {_short_product_name(first.title)}。"


def _short_product_name(title: str) -> str:
    for marker in [" 12.1", " 11", " 高刷", " 学习", " 轻薄"]:
        if marker in title:
            return title.split(marker, 1)[0]
    return _short_text(title, limit=24)


def _safe_json(value: str) -> dict:
    try:
        parsed = json.loads(value or "{}")
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}
