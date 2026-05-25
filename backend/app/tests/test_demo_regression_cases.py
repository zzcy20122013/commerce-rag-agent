import pytest

from app.agents.graph import router_node
from app.agents.intent_router import classify_intent
from app.evaluation.demo_regression_cases import DEMO_REGRESSION_CASES


def test_demo_regression_case_set_has_target_size_and_unique_ids() -> None:
    assert 20 <= len(DEMO_REGRESSION_CASES) <= 30
    assert len({case["case_id"] for case in DEMO_REGRESSION_CASES}) == len(DEMO_REGRESSION_CASES)
    assert all(case["query"].strip() for case in DEMO_REGRESSION_CASES)


@pytest.mark.parametrize("case", DEMO_REGRESSION_CASES, ids=lambda case: case["case_id"])
def test_demo_regression_cases_keep_expected_intent(case: dict) -> None:
    result = classify_intent(case["query"])

    assert result.intent == case["expected_intent"]
    _assert_expected_constraints(result.constraints.model_dump(), case.get("expected_constraints", {}))


@pytest.mark.parametrize(
    "case",
    [case for case in DEMO_REGRESSION_CASES if case.get("memory")],
    ids=lambda case: case["case_id"],
)
def test_demo_regression_cases_keep_expected_routed_intent(case: dict) -> None:
    result = router_node({"query": case["query"], "memory": case["memory"], "trace": []})

    assert result["intent"] == case.get("expected_routed_intent", case["expected_intent"])
    _assert_expected_constraints(result["constraints"], case.get("expected_constraints", {}))


def _assert_expected_constraints(actual: dict, expected: dict) -> None:
    for key, expected_value in expected.items():
        if isinstance(expected_value, list):
            assert all(item in actual.get(key, []) for item in expected_value)
        else:
            assert actual.get(key) == expected_value
