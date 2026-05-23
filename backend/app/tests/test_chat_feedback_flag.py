from app.api.chat import iter_answer_chunks, should_enable_feedback


def test_chitchat_does_not_enable_feedback() -> None:
    result = {"intent": "chitchat", "answer": "你好，我可以帮你挑商品。", "product_cards": []}

    assert should_enable_feedback(result) is False


def test_product_cards_enable_feedback() -> None:
    result = {"intent": "shopping_guide", "answer": "更建议你看第一款。", "product_cards": [{"id": "p1"}]}

    assert should_enable_feedback(result) is True


def test_faq_answer_enables_feedback() -> None:
    result = {"intent": "faq", "answer": "退货政策是七天无理由。", "product_cards": []}

    assert should_enable_feedback(result) is True


def test_answer_chunks_split_long_text_for_visible_streaming() -> None:
    chunks = list(iter_answer_chunks("我想买一台适合学生记笔记的平板电脑"))

    assert len(chunks) > 3
    assert "".join(chunks) == "我想买一台适合学生记笔记的平板电脑"
    assert all(1 <= len(chunk) <= 3 for chunk in chunks)
