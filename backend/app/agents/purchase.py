import re

from sqlalchemy.orm import Session

from app.agents.intent_router import extract_shopping_constraints
from app.agents.shopping_guide import product_to_card
from app.models.tables import Product
from app.services.cart_service import (
    add_cart_item,
    list_cart_items,
    remove_cart_item_by_position,
    update_cart_item_quantity_by_position,
)
from app.services.product_service import find_products_by_query, get_products_by_ids


def purchase_help_node(db: Session):
    def node(state: dict) -> dict:
        query = state["query"]
        action = parse_cart_action(query)
        memory = state.get("memory", {})

        if action == "view":
            return build_cart_state(state, db, trace_action="view")
        if action == "remove":
            position = extract_position(query) or 1
            removed = remove_cart_item_by_position(db, position=position)
            answer = (
                f"已从购物车删除第 {position} 个商品。"
                if removed
                else f"购物车里没有第 {position} 个商品，我没乱删。"
            )
            return build_cart_state(state, db, answer_prefix=answer, trace_action="remove")
        if action == "update":
            position = extract_position(query) or 1
            quantity = extract_quantity(query) or 1
            updated = update_cart_item_quantity_by_position(db, position=position, quantity=quantity)
            answer = (
                f"已把第 {position} 个商品数量改成 {quantity}。"
                if updated
                else f"购物车里没有第 {position} 个商品，数量还没有改。"
            )
            return build_cart_state(state, db, answer_prefix=answer, trace_action="update")

        selected_products = select_products_for_cart(db, query=query, memory=memory)
        if not selected_products:
            return {
                **state,
                "constraints": extract_shopping_constraints(query).model_dump(),
                "memory": memory,
                "retrieved_items": [],
                "product_cards": [],
                "answer": "我还没确定要加哪几款。你可以说“把刚才推荐的都加入购物车”，或者点名商品/说第几个。",
                "trace": state.get("trace", []) + [{"node": "purchase_help", "action": "add", "status": "no_products"}],
            }

        quantity = extract_add_quantity(query) or 1
        for product in selected_products:
            add_cart_item(db, product_id=product.id, quantity=quantity)

        cards = [product_to_card(product, memory, rank) for rank, product in enumerate(selected_products, start=1)]
        names = "、".join(product.title for product in selected_products)
        cart_items = list_cart_items(db)
        return {
            **state,
            "intent": "purchase_help",
            "constraints": extract_shopping_constraints(query).model_dump(),
            "memory": {**memory, "last_cart_product_ids": [product.id for product in selected_products]},
            "retrieved_items": [{"product_id": product.id, "title": product.title} for product in selected_products],
            "product_cards": cards,
            "answer": f"已加入购物车：{names}。{format_added_quantity(quantity)}{format_cart_summary(cart_items)}",
            "trace": state.get("trace", []) + [
                {"node": "purchase_help", "action": "add", "products": [product.id for product in selected_products]}
            ],
        }

    return node


def parse_cart_action(query: str) -> str:
    text = query.lower()
    if any(word in text for word in ["删除", "删掉", "移除", "去掉", "remove"]):
        return "remove"
    if any(word in text for word in ["数量", "改成", "改为", "改到", "加到"]) and re.search(r"\d|一|二|两|三|四|五", text):
        return "update"
    if any(word in text for word in ["查看购物车", "购物车里", "车里", "购物车有什么", "cart"]):
        return "view"
    return "add"


def select_products_for_cart(db: Session, *, query: str, memory: dict) -> list[Product]:
    constraints = extract_shopping_constraints(query).model_dump()
    products = get_products_by_ids(db, constraints.get("product_ids") or [])
    if products:
        return products

    remembered_ids = memory.get("last_product_ids") or memory.get("last_cart_product_ids") or []
    products = get_products_by_ids(db, remembered_ids)
    if not products:
        products = find_products_by_query(db, query, limit=3)

    quotas = extract_category_quotas(query)
    if quotas and products:
        selected: list[Product] = []
        selected_ids = set()
        for category_key, count in quotas:
            matches = [product for product in products if product.id not in selected_ids and product_matches_cart_term(product, category_key)]
            for product in matches[:count]:
                selected.append(product)
                selected_ids.add(product.id)
        return selected

    if asks_for_all(query):
        return products[:5]
    return products[:1]


def extract_category_quotas(query: str) -> list[tuple[str, int]]:
    quotas: list[tuple[str, int]] = []
    for raw_count, raw_name in re.findall(r"([一二两三四五六七八九十\d]+)\s*个?\s*(裤子|裤|裙子|裙|鞋|耳机|平板|精华|商品)", query):
        quotas.append((raw_name, chinese_number_to_int(raw_count)))
    return quotas


def product_matches_cart_term(product: Product, term: str) -> bool:
    haystack = f"{product.title} {product.category} {product.description}".lower()
    aliases = {
        "裤子": ["裤", "长裤", "短裤"],
        "裤": ["裤", "长裤", "短裤"],
        "裙子": ["裙"],
        "裙": ["裙"],
        "鞋": ["鞋", "跑鞋", "通勤鞋"],
        "耳机": ["耳机"],
        "平板": ["平板"],
        "精华": ["精华"],
        "商品": [""],
    }
    return any(alias in haystack for alias in aliases.get(term, [term]))


def asks_for_all(query: str) -> bool:
    return any(word in query for word in ["都加入", "全部加入", "全加", "刚才推荐的都", "这几个都"])


def extract_position(query: str) -> int | None:
    position_words = {
        "第一个": 1,
        "第一": 1,
        "第二个": 2,
        "第二": 2,
        "第三个": 3,
        "第三": 3,
        "第四个": 4,
        "第四": 4,
    }
    for word, position in position_words.items():
        if word in query:
            return position
    match = re.search(r"第\s*(\d+)\s*个?", query)
    return int(match.group(1)) if match else None


def extract_quantity(query: str) -> int | None:
    patterns = [
        r"数量\s*(?:改成|改为|改到)?\s*([一二两三四五六七八九十\d]+)",
        r"(?:改成|改为|改到|加到)\s*([一二两三四五六七八九十\d]+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, query)
        if match:
            return chinese_number_to_int(match.group(1))
    return None


def extract_add_quantity(query: str) -> int | None:
    patterns = [
        r"(?:加入|加购|加|买|来)\s*([一二两三四五六七八九十百\d]+)\s*(?:件|个|份|箱|包|瓶|双)?",
        r"([一二两三四五六七八九十百\d]+)\s*(?:件|个|份|箱|包|瓶|双)\s*(?:加入|加购|加到|放进|放入)",
    ]
    for pattern in patterns:
        match = re.search(pattern, query)
        if match:
            quantity = chinese_number_to_int(match.group(1))
            return quantity if quantity > 0 else None
    return None


def format_added_quantity(quantity: int) -> str:
    return "" if quantity == 1 else f"本次每款加入 {quantity} 件。"


def chinese_number_to_int(value: str) -> int:
    if value.isdigit():
        return int(value)
    if value == "一百":
        return 100
    if value.endswith("百") and len(value) == 2:
        mapping = {"一": 1, "二": 2, "两": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9}
        return mapping.get(value[0], 1) * 100
    mapping = {"一": 1, "二": 2, "两": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9, "十": 10}
    return mapping.get(value, 1)


def build_cart_state(state: dict, db: Session, *, answer_prefix: str = "", trace_action: str) -> dict:
    cart_items = list_cart_items(db)
    prefix = f"{answer_prefix} " if answer_prefix else ""
    return {
        **state,
        "intent": "purchase_help",
        "retrieved_items": [
            {"product_id": item["product"]["id"], "quantity": item["quantity"]}
            for item in cart_items
        ],
        "product_cards": [],
        "answer": prefix + format_cart_summary(cart_items),
        "trace": state.get("trace", []) + [{"node": "purchase_help", "action": trace_action, "cart_count": len(cart_items)}],
    }


def format_cart_summary(cart_items: list[dict]) -> str:
    if not cart_items:
        return "购物车现在是空的。"
    lines = []
    total = 0
    for index, item in enumerate(cart_items, start=1):
        product = item["product"]
        subtotal = item["subtotal"]
        total += subtotal
        lines.append(f"{index}. {product['title']} x {item['quantity']}，小计 {subtotal} 元")
    return f"当前购物车：{'；'.join(lines)}。合计约 {total} 元。"
