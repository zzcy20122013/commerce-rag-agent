from app.agents.response_composer import compose_agent_response, stream_response_composer_chunks
from app.llm.generation import _format_llm_error, generate_response_composer_result
from app.llm.prompt_registry import build_response_composer_messages
import httpx


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


class FakeStreamClient:
    def __init__(self, chunks: list[str] | None = None, *, should_fail: bool = False):
        self.chunks = chunks or ["我会", "优先看", "第一款"]
        self.should_fail = should_fail
        self.messages = []

    def stream_chat_sync(self, messages: list[dict[str, str]], *, temperature: float = 0.2):
        self.messages = messages
        if self.should_fail:
            raise TimeoutError("stream timeout")
        yield from self.chunks


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


def test_response_composer_does_not_rewrite_multimodal_search_answers() -> None:
    client = FakeChatClient("我又写出了 VLM。")
    result = {
        "intent": "multimodal_search",
        "answer": "这张图的细节不算特别清楚，我先按外观相近的方向帮你找。",
        "memory": {},
        "product_cards": [{"product_id": "p1", "title": "缓震跑鞋", "price": 899}],
        "retrieved_items": [],
        "trace": [{"node": "multimodal_search"}],
    }

    composed = compose_agent_response(query="找类似的鞋", result=result, client=client)
    completed = {}
    chunks = list(stream_response_composer_chunks(query="找类似的鞋", result=result, client=client, on_complete=completed.update))

    assert composed["answer"] == result["answer"]
    assert "".join(chunks) == result["answer"]
    assert composed["response_composer"]["llm_enabled"] is False
    assert completed["llm_enabled"] is False
    assert client.messages == []


def test_response_composer_falls_back_when_llm_leaks_internal_fields() -> None:
    client = FakeChatClient(
        "OPPO Find X9 Ultra 的核心信息如下：价格 6999 元。\n\n"
        "参数：sub_category: 智能手机, sku_count: 4, sku_options: ['12GB+256GB 标准版']。\n"
        "知识库补充：商品ID: p_digital_015，review_summary: {'negative_review_count': 2}。"
    )
    fallback = "您可以优先看 OPPO Find X9 Ultra，价格 6999 元。它拍照和续航都比较强，但屏幕偏大。"

    result = generate_response_composer_result(
        query="有没有便宜一点的，最好拍照好、续航久，不要太大屏",
        intent="shopping_guide",
        draft_answer=fallback,
        memory={"budget_max": 8000},
        product_cards=[],
        retrieved_items=[],
        fallback=fallback,
        client=client,
    )

    assert result.content == fallback
    assert result.llm_enabled is False
    assert result.llm_error == "unsafe_generated_answer"


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


def test_response_composer_streams_llm_chunks_and_reports_metadata() -> None:
    client = FakeStreamClient(["主推", "第一款"])
    completed = {}
    result = {
        "intent": "shopping_guide",
        "answer": "我会先看第一款。",
        "memory": {},
        "product_cards": [{"product_id": "p1", "title": "通勤鞋", "price": 269}],
        "retrieved_items": [],
        "trace": [{"node": "shopping_guide"}],
    }

    chunks = list(stream_response_composer_chunks(query="推荐通勤鞋", result=result, client=client, on_complete=completed.update))

    assert "".join(chunks) == "主推第一款"
    assert completed["answer"] == "主推第一款"
    assert completed["llm_enabled"] is True
    assert completed["llm_error"] is None
    assert "通勤鞋" in client.messages[1]["content"]


def test_response_composer_stream_falls_back_when_streaming_fails() -> None:
    client = FakeStreamClient(should_fail=True)
    completed = {}
    result = {
        "intent": "shopping_guide",
        "answer": "我会先看第一款。",
        "memory": {},
        "product_cards": [],
        "retrieved_items": [],
        "trace": [],
    }

    chunks = list(stream_response_composer_chunks(query="推荐通勤鞋", result=result, client=client, on_complete=completed.update))

    assert "".join(chunks) == "我会先看第一款。"
    assert completed["answer"] == "我会先看第一款。"
    assert completed["llm_enabled"] is False
    assert "stream timeout" in completed["llm_error"]


def test_response_composer_stream_falls_back_when_chunks_leak_internal_fields() -> None:
    client = FakeStreamClient(
        [
            "OPPO Find X9 Ultra 的核心信息如下：",
            "参数：sub_category: 智能手机, sku_options: ['12GB+256GB']。",
            "知识库补充：商品ID: p_digital_015。",
        ]
    )
    completed = {}
    result = {
        "intent": "shopping_guide",
        "answer": "您可以优先看 OPPO Find X9 Ultra，价格 6999 元。它拍照和续航都比较强，但屏幕偏大。",
        "memory": {},
        "product_cards": [],
        "retrieved_items": [],
        "trace": [],
    }

    chunks = list(stream_response_composer_chunks(query="推荐手机", result=result, client=client, on_complete=completed.update))

    assert "".join(chunks) == result["answer"]
    assert completed["answer"] == result["answer"]
    assert completed["llm_enabled"] is False
    assert completed["llm_error"] == "unsafe_generated_answer"


def test_llm_error_format_does_not_read_unconsumed_stream_response() -> None:
    request = httpx.Request("POST", "https://example.test/chat/completions")
    response = httpx.Response(500, request=request, stream=httpx.ByteStream(b'{"error":"bad"}'))
    error = httpx.HTTPStatusError("server error", request=request, response=response)

    formatted = _format_llm_error(error)

    assert formatted == "http_500: <stream response body not read>"
