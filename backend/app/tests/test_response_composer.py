from app.agents.response_composer import compose_agent_response


class FakeChatClient:
    def __init__(self, answer: str = "我会优先推荐第一款，理由更贴合你的预算和用途。", *, should_fail: bool = False):
        self.answer = answer
        self.should_fail = should_fail
        self.messages = []

    def chat_sync(self, messages: list[dict[str, str]], *, temperature: float = 0.2) -> str:
        self.messages = messages
        if self.should_fail:
            raise RuntimeError("composer unavailable")
        return self.answer


def test_response_composer_rewrites_visible_answer_with_llm() -> None:
    client = FakeChatClient()
    result = {
        "intent": "compare",
        "answer": "商品A价格低。商品B评分高。",
        "memory": {"budget_max": 300},
        "product_cards": [{"product_id": "p1", "title": "通勤鞋", "price": 269}],
        "retrieved_items": [],
        "trace": [{"node": "compare"}],
    }

    composed = compose_agent_response(query="这两个哪个好", result=result, client=client)

    assert composed["answer"] == "我会优先推荐第一款，理由更贴合你的预算和用途。"
    assert composed["response_composer"]["llm_enabled"] is True
    assert composed["trace"][-1]["node"] == "response_composer"
    assert "商品A价格低" in client.messages[1]["content"]
    assert "通勤鞋" in client.messages[1]["content"]


def test_response_composer_keeps_original_answer_when_llm_fails() -> None:
    client = FakeChatClient(should_fail=True)
    result = {
        "intent": "order_query",
        "answer": "订单已发货，正在运输中。",
        "memory": {},
        "product_cards": [],
        "retrieved_items": [],
        "trace": [{"node": "order"}],
    }

    composed = compose_agent_response(query="订单到哪了", result=result, client=client)

    assert composed["answer"] == "订单已发货，正在运输中。"
    assert composed["response_composer"]["llm_enabled"] is False
    assert "composer unavailable" in composed["response_composer"]["llm_error"]
