from app.evaluation.guide_eval_metrics import score_guide_case, summarize_guide_results


def test_score_guide_case_passes_human_guide_recommendation() -> None:
    case = {
        "case_id": "guide_unit_001",
        "expected_intent": "shopping_guide",
        "expected_terms": ["平板"],
        "budget_max": 3500,
        "min_cards": 1,
        "expected_no_exact_match": False,
    }
    result = {
        "intent": "shopping_guide",
        "answer": "我更推荐你优先看这款学生平板，记笔记和网课都够用；备选可以看轻薄款。",
        "product_cards": [
            {"product_id": "p_tablet_001", "title": "学生记笔记平板", "subtitle": "适合网课", "price": 2199}
        ],
        "memory": {"budget_max": 3500, "category": "数码电子"},
        "no_exact_match": False,
    }

    scored = score_guide_case(case, result)

    assert scored["passed"] is True
    assert scored["failed_checks"] == []


def test_score_guide_case_fails_when_no_exact_match_has_no_explanation() -> None:
    case = {
        "case_id": "guide_unit_002",
        "expected_intent": "shopping_guide",
        "expected_terms": ["通勤鞋"],
        "budget_max": 300,
        "min_cards": 1,
        "expected_no_exact_match": True,
    }
    result = {
        "intent": "shopping_guide",
        "answer": "我更推荐这双通勤鞋，脚感不错。",
        "product_cards": [
            {"product_id": "p_shoe_001", "title": "通勤鞋", "subtitle": "缓震", "price": 499}
        ],
        "memory": {"budget_max": 300, "category": "服饰运动"},
        "no_exact_match": False,
    }

    scored = score_guide_case(case, result)

    assert scored["passed"] is False
    assert "no_exact_match_ok" in scored["failed_checks"]
    assert "style_ok" in scored["failed_checks"]


def test_summarize_guide_results_counts_rates() -> None:
    summary = summarize_guide_results([
        {"passed": True, "intent_ok": True, "style_ok": True, "cart_ok": True},
        {"passed": False, "intent_ok": True, "style_ok": False, "cart_ok": True},
        {"passed": "false", "intent_ok": "true", "style_ok": "false", "cart_ok": "true"},
    ])

    assert summary["guide_total_cases"] == 3
    assert summary["guide_pass_rate"] == 0.3333
    assert summary["guide_style_rate"] == 0.3333
