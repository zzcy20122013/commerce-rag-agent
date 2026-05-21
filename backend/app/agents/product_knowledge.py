import json

from sqlalchemy.orm import Session

from app.agents.shopping_guide import product_to_card
from app.services.product_service import find_products_by_query, get_product_knowledge_docs, get_product_tags, get_products_by_ids


def product_knowledge_node(db: Session):
    def node(state: dict) -> dict:
        query = state["query"]
        memory_product_ids = state.get("memory", {}).get("last_product_ids", [])[:3]
        products = get_products_by_ids(db, memory_product_ids) if is_followup_product_question(query) else []
        if not products:
            products = find_products_by_query(db, query, limit=3)
        if not products:
            products = get_products_by_ids(db, memory_product_ids)
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
        docs = get_product_knowledge_docs(db, product.id, limit=4)
        answer = build_product_knowledge_answer(product, specs, tags, docs, query=query)
        cards = [product_to_card(item, state.get("memory", {}), rank) for rank, item in enumerate(products, start=1)]
        memory = {**state.get("memory", {}), "last_product_ids": [product.id for product in products]}
        retrieved_docs = [
            {"id": doc["id"], "text": doc["text"], "source": "documents", "metadata": doc["metadata"]}
            for doc in docs
        ]
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
            ]
            + retrieved_docs,
            "product_cards": cards,
            "answer": answer,
            "trace": state.get("trace", []) + [
                {
                    "node": "product_knowledge",
                    "product_id": product.id,
                    "sources": ["products", "product_tags", "documents"],
                    "doc_hits": [doc["id"] for doc in docs],
                }
            ],
        }

    return node


def build_product_knowledge_answer(product, specs: dict, tags: list, docs: list[dict], *, query: str) -> str:
    spec_text = "、".join(f"{key}: {value}" for key, value in specs.items()) if specs else "暂无结构化参数"
    tag_text = "、".join(tag.value for tag in tags[:6]) if tags else "暂无标签"
    doc_text = select_relevant_doc_text(query, docs)
    return (
        f"{product.title} 的核心信息如下：价格 {product.price} 元，评分 {product.rating}，库存 {product.stock}。"
        f"商品说明：{product.description} 参数：{spec_text}。相关标签：{tag_text}。"
        f"{doc_text}"
    )


def select_relevant_doc_text(query: str, docs: list[dict]) -> str:
    if not docs:
        return ""
    lowered = query.lower()
    scored = []
    for doc in docs:
        text = doc.get("text", "")
        score = sum(1 for keyword in ["敏感肌", "修护", "维稳", "保湿", "防晒", "控油", "FAQ", "评价"] if keyword in lowered and keyword in text)
        score += sum(1 for char in set(lowered) if char.strip() and char in text) / 100
        scored.append((score, text))
    selected = [text for _, text in sorted(scored, key=lambda item: item[0], reverse=True)[:2] if text]
    if not selected:
        return ""
    snippets = " ".join(text.replace("\n", " ")[:220] for text in selected)
    return f" 知识库补充：{snippets}"


def is_followup_product_question(query: str) -> bool:
    return any(keyword in query for keyword in ["这款", "这个", "它", "该商品", "怎么用", "如何使用", "用法"])


def _safe_json(value: str) -> dict:
    try:
        parsed = json.loads(value or "{}")
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}
