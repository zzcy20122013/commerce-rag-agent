from app.agents.response_composer import compose_agent_response
from app.llm.prompt_registry import build_response_composer_messages


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


def test_response_composer_does_not_rewrite_purchase_cart_actions() -> None:
    client = FakeChatClient("我改写了购物车数量。")
    result = {
        "intent": "purchase_help",
        "answer": "已把第 1 个商品数量改成 2。当前购物车：通勤直筒裤 x 2。",
        "memory": {},
        "product_cards": [],
        "retrieved_items": [],
        "trace": [{"node": "purchase_help"}],
    }

    composed = compose_agent_response(query="把第一个数量改成2", result=result, client=client)

    assert composed["answer"] == result["answer"]
    assert composed["response_composer"]["llm_enabled"] is False
    assert composed["trace"][-1]["node"] == "response_composer"
    assert composed["trace"][-1]["reason"] == "transactional_answer_preserved"
    assert client.messages == []


def test_response_composer_prompt_keeps_guide_decision_rules() -> None:
    messages = build_response_composer_messages(
        query="300以内通勤鞋，有没有更稳的",
        intent="shopping_guide",
        draft_answer="没有严格符合条件的商品，第一款超预算。",
        memory={"budget_max": 300, "no_exact_match": True},
        product_cards=[{"product_id": "p1", "title": "通勤鞋", "price": 329}],
        retrieved_items=[],
    )

    system_prompt = messages[0]["content"]
    assert "主推" in system_prompt
    assert "备选" in system_prompt
    assert "劝退" in system_prompt
    assert "没有严格符合条件" in system_prompt
    assert "商品卡片里的推荐理由" in system_prompt
    assert "不要写成检索报告" in system_prompt
