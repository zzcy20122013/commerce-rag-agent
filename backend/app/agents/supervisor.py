from typing import Any


SPECIALIST_TOOLS = {
    "shopping_guide": ["catalog_filter", "hybrid_keyword_vector_retrieval", "grounded_card_answer"],
    "decision_guide": ["guide_sop", "hybrid_keyword_vector_retrieval", "clarifying_question"],
    "product_knowledge": ["product_lookup", "review_summary", "grounded_fact_check"],
    "compare": ["product_lookup", "spec_compare", "review_compare"],
    "purchase_help": ["cart_crud", "checkout_state_machine", "stock_reservation"],
    "order_query": ["order_lookup"],
    "faq": ["policy_rag"],
    "clarification": ["slot_check"],
    "chitchat": ["safe_smalltalk"],
}


def build_supervisor_trace(
    *,
    query: str,
    intent: str,
    memory: dict[str, Any] | None = None,
    has_image: bool = False,
) -> dict[str, Any]:
    memory = memory or {}
    specialist = _specialist_for_intent(intent)
    return {
        "node": "supervisor",
        "specialist": specialist,
        "intent": intent,
        "agentic_rag_plan": {
            "retrieval_strategy": _retrieval_strategy(intent, memory, has_image),
            "tools": SPECIALIST_TOOLS.get(specialist, ["safe_smalltalk"]),
            "guardrails": _guardrails_for_intent(intent, memory),
            "handoff_reason": _handoff_reason(query, intent, memory, has_image),
        },
    }


def _specialist_for_intent(intent: str) -> str:
    return intent if intent in SPECIALIST_TOOLS else "chitchat"


def _retrieval_strategy(intent: str, memory: dict[str, Any], has_image: bool) -> str:
    if has_image:
        return "image_vector_plus_vision_text_rerank"
    if intent in {"shopping_guide", "decision_guide", "product_knowledge", "compare"}:
        if memory.get("category") or memory.get("subcategory") or memory.get("budget_max"):
            return "sql_filter_plus_bm25_plus_vector_rerank"
        return "bm25_plus_vector_recall"
    if intent == "faq":
        return "policy_document_rag"
    return "no_retrieval"


def _guardrails_for_intent(intent: str, memory: dict[str, Any]) -> list[str]:
    guardrails = ["trace_persisted", "grounded_answer"]
    if intent == "purchase_help":
        guardrails.extend(["cart_state_checked", "stock_checked"])
    if intent in {"shopping_guide", "decision_guide", "compare", "product_knowledge"}:
        guardrails.extend(["product_card_source_only", "low_confidence_flag"])
    if memory.get("budget_max"):
        guardrails.append("budget_constraint_checked")
    return list(dict.fromkeys(guardrails))


def _handoff_reason(query: str, intent: str, memory: dict[str, Any], has_image: bool) -> str:
    if has_image:
        return "user_uploaded_image"
    if intent == "purchase_help":
        return "commerce_command_detected"
    if memory.get("category") or memory.get("subcategory"):
        return "shopping_constraints_detected"
    if intent == "compare":
        return "comparison_intent_detected"
    if intent == "product_knowledge":
        return "product_fact_question_detected"
    return "intent_router_default"
