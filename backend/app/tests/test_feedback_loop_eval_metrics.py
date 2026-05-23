from app.evaluation.feedback_loop_eval_metrics import analyze_feedback_rows


def test_analyze_feedback_rows_counts_reason_coverage() -> None:
    summary = analyze_feedback_rows([
        {"feedback_id": "fb_1", "rating": 1, "reason": ""},
        {"feedback_id": "fb_2", "rating": -1, "reason": "太贵"},
        {"feedback_id": "fb_3", "rating": -1, "reason": "不相关"},
    ])

    assert summary["feedback_total"] == 3
    assert summary["feedback_positive_count"] == 1
    assert summary["feedback_negative_count"] == 2
    assert summary["feedback_positive_rate"] == 0.3333
    assert summary["feedback_negative_reason_coverage"] == 1.0
    assert summary["reason_太贵"] == 1
    assert summary["reason_不相关"] == 1


def test_analyze_feedback_rows_handles_empty_rows() -> None:
    summary = analyze_feedback_rows([])

    assert summary["feedback_total"] == 0
    assert summary["feedback_positive_rate"] == 0.0
    assert summary["feedback_negative_reason_coverage"] == 0.0
