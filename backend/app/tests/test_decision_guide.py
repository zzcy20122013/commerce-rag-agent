from app.agents.decision_guide import build_decision_fallback


def test_decision_fallback_uses_user_facing_recommendation_tone() -> None:
    answer = build_decision_fallback(
        [
            {"title": "学生轻薄平板", "price": 2199},
            {"title": "影音高刷平板", "price": 3299},
        ],
        {"subcategory": "平板"},
    )

    assert "您可以优先看" in answer
    assert "我会优先" not in answer
    assert "我会先看" not in answer
