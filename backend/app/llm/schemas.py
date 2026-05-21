from typing import Literal

from pydantic import BaseModel, Field


IntentLabel = Literal[
    "shopping_guide",
    "decision_guide",
    "faq",
    "product_knowledge",
    "compare",
    "order_query",
    "purchase_help",
    "clarification",
    "chitchat",
]


class ShoppingConstraints(BaseModel):
    category: str | None = None
    subcategory: str | None = None
    budget_max: int | None = None
    use_cases: list[str] = Field(default_factory=list)
    audience: str | None = None
    preferences: list[str] = Field(default_factory=list)
    product_ids: list[str] = Field(default_factory=list)
    strict_filter: bool = False


class IntentResult(BaseModel):
    intent: IntentLabel
    confidence: float
    constraints: ShoppingConstraints = Field(default_factory=ShoppingConstraints)
