from app.agents.chitchat import chitchat_node


class FakeChatClient:
    def __init__(self, answer: str = "你好，我在，先告诉我预算和想买的品类就行。", *, should_fail: bool = False):
        self.answer = answer
        self.should_fail = should_fail
        self.messages = []

    def chat_sync(self, messages: list[dict[str, str]], *, temperature: float = 0.2) -> str:
        self.messages = messages
        if self.should_fail:
            raise RuntimeError("llm down")
        return self.answer


def test_chitchat_uses_llm_when_client_is_available() -> None:
    client = FakeChatClient("在的，你直接说想买什么，我帮你按预算和用途挑。")

    result = chitchat_node({"query": "你好", "trace": []}, client=client)

    assert result["answer"] == "在的，你直接说想买什么，我帮你按预算和用途挑。"
    assert result["llm_enabled"] is True
    assert client.messages[0]["role"] == "system"
    assert "真人导购" in client.messages[0]["content"]
    assert "你好" in client.messages[1]["content"]


def test_chitchat_falls_back_when_llm_fails() -> None:
    client = FakeChatClient(should_fail=True)

    result = chitchat_node({"query": "你好", "trace": []}, client=client)

    assert result["llm_enabled"] is False
    assert "你好" in result["answer"]


def test_greeting_chitchat_replies_naturally() -> None:
    result = chitchat_node({"query": "你好", "trace": []})

    assert "你好" in result["answer"]
    assert "预算" in result["answer"]
    assert "用途" in result["answer"]
    assert "品牌偏好" not in result["answer"]


def test_thanks_chitchat_replies_as_assistant() -> None:
    result = chitchat_node({"query": "谢谢", "trace": []})

    assert "不客气" in result["answer"]
    assert "商品" in result["answer"]
