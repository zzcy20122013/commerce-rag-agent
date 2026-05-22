from app.llm.generation import ChatClient, generate_chitchat_result


def chitchat_node(state: dict, *, client: ChatClient | None = None) -> dict:
    query = str(state.get("query", "")).strip().lower()
    fallback = _fallback_answer(query)
    generation = generate_chitchat_result(query=query, fallback=fallback, client=client)
    trace_item = {"node": "chitchat", "llm_enabled": generation.llm_enabled}
    if generation.llm_error:
        trace_item["llm_error"] = generation.llm_error
    return {
        **state,
        "answer": generation.content,
        "llm_enabled": generation.llm_enabled,
        "product_cards": [],
        "trace": state.get("trace", []) + [trace_item],
    }


def _fallback_answer(query: str) -> str:
    if _is_greeting(query):
        return "你好呀，我在。你可以直接告诉我想买什么、预算大概多少、主要用途是什么，我会帮你挑出更合适的几款。"
    elif _is_thanks(query):
        return "不客气。后面你看中哪个商品，也可以继续问我适不适合、值不值得买，或者让我帮你做对比。"
    return "我在，可以继续说你的购物需求。比如预算、用途、偏好的品牌或不想踩的坑，我会按这些条件帮你挑。"


def _is_greeting(text: str) -> bool:
    greetings = ["你好", "您好", "hello", "hi", "嗨", "在吗", "在不在"]
    return any(word in text for word in greetings)


def _is_thanks(text: str) -> bool:
    thanks = ["谢谢", "感谢", "多谢", "thank", "辛苦"]
    return any(word in text for word in thanks)
