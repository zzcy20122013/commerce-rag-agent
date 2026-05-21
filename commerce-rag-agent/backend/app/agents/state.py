from typing import Any, TypedDict


class AgentState(TypedDict, total=False):
    messages: list[dict[str, str]]
    query: str
    intent: str
    constraints: dict[str, Any]
    memory: dict[str, Any]
    retrieved_items: list[dict[str, Any]]
    product_cards: list[dict[str, Any]]
    comparison: dict[str, Any]
    no_exact_match: bool
    answer: str
    trace: list[dict[str, Any]]
