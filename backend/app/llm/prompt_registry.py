from app.llm.prompt_blocks import (
    BUDGET_RULES,
    DECISION_GUIDE_TASK,
    DECISION_USER_REQUIREMENTS,
    FAQ_TASK,
    GROUNDING_RULES,
    SHOPPING_GUIDE_TASK,
    SHOPPING_OUTPUT_RULES,
    SHOPPING_PERSONA,
    SHOPPING_STYLE_RULES,
    SHOPPING_USER_REQUIREMENTS,
)


def build_shopping_messages(*, query: str, cards: list[dict], memory: dict) -> list[dict[str, str]]:
    return [
        {
            "role": "system",
            "content": build_system_prompt(
                SHOPPING_PERSONA,
                GROUNDING_RULES,
                SHOPPING_GUIDE_TASK,
                SHOPPING_STYLE_RULES,
                BUDGET_RULES,
                SHOPPING_OUTPUT_RULES,
            ),
        },
        {
            "role": "user",
            "content": (
                f"用户问题：{query}\n"
                f"已提取约束：{memory}\n"
                f"候选商品卡片：{cards}\n"
                f"{SHOPPING_USER_REQUIREMENTS.strip()}"
            ),
        },
    ]


def build_decision_guide_messages(*, query: str, cards: list[dict], memory: dict) -> list[dict[str, str]]:
    return [
        {
            "role": "system",
            "content": build_system_prompt(
                SHOPPING_PERSONA,
                GROUNDING_RULES,
                DECISION_GUIDE_TASK,
            ),
        },
        {
            "role": "user",
            "content": (
                f"用户问题：{query}\n"
                f"已知用户约束：{memory}\n"
                f"当前商品库可推荐卡片：{cards}\n"
                f"{DECISION_USER_REQUIREMENTS.strip()}"
            ),
        },
    ]


def build_faq_messages(*, query: str, hits: list[dict]) -> list[dict[str, str]]:
    context = "\n".join(hit.get("text", "") for hit in hits)
    return [
        {
            "role": "system",
            "content": build_system_prompt(FAQ_TASK),
        },
        {
            "role": "user",
            "content": f"用户问题：{query}\n检索上下文：\n{context}\n请给出准确、简洁的回答。",
        },
    ]


def build_system_prompt(*blocks: str) -> str:
    return "\n".join(block.strip() for block in blocks if block.strip())
