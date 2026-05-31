from app.agents.graph import router_node


def test_router_adds_supervisor_trace_for_agentic_rag_explainability() -> None:
    result = router_node(
        {
            "query": "帮我推荐 2000 以内通勤降噪耳机",
            "messages": [],
            "memory": {},
            "trace": [],
        }
    )

    supervisor = next(item for item in result["trace"] if item.get("node") == "supervisor")
    assert supervisor["specialist"] == "shopping_guide"
    assert "bm25" in supervisor["agentic_rag_plan"]["retrieval_strategy"]
    assert "low_confidence_flag" in supervisor["agentic_rag_plan"]["guardrails"]
