from sqlalchemy.orm import Session

from app.agents.intent_router import extract_shopping_constraints
from app.agents.shopping_guide import product_to_card
from app.services.product_service import find_products_by_query, get_products_by_ids


def purchase_help_node(db: Session):
    def node(state: dict) -> dict:
        query = state["query"]
        constraints = extract_shopping_constraints(query).model_dump()
        product_ids = constraints.get("product_ids") or state.get("memory", {}).get("last_product_ids", [])
        products = get_products_by_ids(db, product_ids[:3])
        if not products:
            products = find_products_by_query(db, query, limit=3)

        cards = [product_to_card(product, state.get("memory", {}), rank) for rank, product in enumerate(products, start=1)]
        return {
            **state,
            "constraints": constraints,
            "memory": {**state.get("memory", {}), "last_product_ids": [product.id for product in products] or product_ids},
            "retrieved_items": [{"product_id": product.id, "title": product.title} for product in products],
            "product_cards": cards,
            "answer": build_purchase_answer(products),
            "trace": state.get("trace", []) + [
                {"node": "purchase_help", "products": [product.id for product in products]}
            ],
        }

    return node


def build_purchase_answer(products) -> str:
    if not products:
        return (
            "当前 Web Debug 还没有接入真实支付和购物车。你可以先告诉我想购买哪一款，"
            "我会继续帮你确认商品、预算、库存和是否适合下单。"
        )

    names = "、".join(product.title for product in products[:3])
    return (
        "当前这是导购 Agent 的调试界面，还没有接入真实电商交易、购物车和支付。"
        f"如果要购买，可以先从上面的商品卡片里选定一款，例如：{names}。"
        "合理的下单流程是：1. 确认商品和规格；2. 查看库存与价格；3. 进入商品详情页；"
        "4. 加入购物车或立即购买；5. 提交订单并支付。"
        "后续正式展示端会把这里接到商品详情页、购物车/订单接口和支付占位流程。"
    )
