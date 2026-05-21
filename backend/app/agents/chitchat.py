def chitchat_node(state: dict) -> dict:
    return {
        **state,
        "answer": "我可以帮你按预算、用途、品牌偏好来挑商品，也可以解释商品参数和售后政策。",
        "product_cards": [],
        "trace": state.get("trace", []) + [{"node": "chitchat"}],
    }
