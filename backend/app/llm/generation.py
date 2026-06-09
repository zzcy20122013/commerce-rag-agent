import os
from dataclasses import dataclass
from typing import Protocol

import httpx
from dotenv import load_dotenv

from app.llm.openai_compatible_client import OpenAICompatibleClient
from app.llm.prompt_registry import (
    build_chitchat_messages,
    build_decision_guide_messages,
    build_faq_messages,
    build_response_composer_messages,
    build_shopping_messages,
)


load_dotenv()


class ChatClient(Protocol):
    def chat_sync(self, messages: list[dict[str, str]], *, temperature: float = 0.2) -> str:
        ...


@dataclass(frozen=True)
class GenerationResult:
    content: str
    llm_enabled: bool
    llm_error: str | None = None


def generate_shopping_answer(
    *,
    query: str,
    cards: list[dict],
    memory: dict,
    fallback: str,
    client: ChatClient | None = None,
) -> str:
    return generate_shopping_result(
        query=query,
        cards=cards,
        memory=memory,
        fallback=fallback,
        client=client,
    ).content


def generate_shopping_result(
    *,
    query: str,
    cards: list[dict],
    memory: dict,
    fallback: str,
    client: ChatClient | None = None,
) -> GenerationResult:
    return _generate_result(
        messages=build_shopping_messages(query=query, cards=cards, memory=memory),
        fallback=fallback,
        client=client,
    )


def generate_decision_guide_result(
    *,
    query: str,
    cards: list[dict],
    memory: dict,
    fallback: str,
    client: ChatClient | None = None,
) -> GenerationResult:
    return _generate_result(
        messages=build_decision_guide_messages(query=query, cards=cards, memory=memory),
        fallback=fallback,
        client=client,
    )


def generate_chitchat_result(
    *,
    query: str,
    fallback: str,
    client: ChatClient | None = None,
) -> GenerationResult:
    return _generate_result(
        messages=build_chitchat_messages(query=query),
        fallback=fallback,
        client=client,
    )


def generate_faq_answer(
    *,
    query: str,
    hits: list[dict],
    fallback: str,
    client: ChatClient | None = None,
) -> str:
    return generate_faq_result(query=query, hits=hits, fallback=fallback, client=client).content


def generate_response_composer_result(
    *,
    query: str,
    intent: str,
    draft_answer: str,
    memory: dict,
    product_cards: list[dict],
    retrieved_items: list,
    fallback: str,
    comparison: dict | None = None,
    client: ChatClient | None = None,
) -> GenerationResult:
    return _generate_result(
        messages=build_response_composer_messages(
            query=query,
            intent=intent,
            draft_answer=draft_answer,
            memory=memory,
            product_cards=product_cards,
            retrieved_items=retrieved_items,
            comparison=comparison,
        ),
        fallback=fallback,
        client=client,
    )


def generate_faq_result(
    *,
    query: str,
    hits: list[dict],
    fallback: str,
    client: ChatClient | None = None,
) -> GenerationResult:
    return _generate_result(
        messages=build_faq_messages(query=query, hits=hits),
        fallback=fallback,
        client=client,
    )


def _generate(*, messages: list[dict[str, str]], fallback: str, client: ChatClient | None) -> str:
    return _generate_result(messages=messages, fallback=fallback, client=client).content


def _generate_result(
    *,
    messages: list[dict[str, str]],
    fallback: str,
    client: ChatClient | None,
) -> GenerationResult:
    if client is None and not _has_provider_key():
        return GenerationResult(content=fallback, llm_enabled=False, llm_error="missing_api_key")
    try:
        resolved_client = client or _build_default_client()
        answer = resolved_client.chat_sync(messages, temperature=0.2).strip()
        if not answer:
            return GenerationResult(content=fallback, llm_enabled=False, llm_error="empty_response")
        if _contains_internal_artifacts(answer):
            return GenerationResult(content=fallback, llm_enabled=False, llm_error="unsafe_generated_answer")
        return GenerationResult(content=answer, llm_enabled=True)
    except Exception as error:
        return GenerationResult(content=fallback, llm_enabled=False, llm_error=_format_llm_error(error))


def _build_default_client() -> ChatClient:
    return OpenAICompatibleClient()


def _has_provider_key() -> bool:
    return bool(os.getenv("DOUBAO_API_KEY") or os.getenv("ARK_API_KEY"))


def _format_llm_error(error: Exception) -> str:
    if isinstance(error, httpx.HTTPStatusError):
        try:
            body = error.response.text.replace("\n", " ")[:500]
        except httpx.ResponseNotRead:
            body = "<stream response body not read>"
        return f"http_{error.response.status_code}: {body}"
    return f"{type(error).__name__}: {str(error)[:500]}"


def _contains_internal_artifacts(answer: str) -> bool:
    text = answer or ""
    internal_markers = [
        "sku_",
        "review_summary",
        "negative_review_count",
        "negative_keywords",
        "商品ID",
        "知识库补充",
        "相关标签",
        "检索结果",
        "候选商品",
        "结构化字段",
        "数据库",
    ]
    if any(marker in text for marker in internal_markers):
        return True
    return bool("参数" in text and any(marker in text for marker in ["sub_category", "sku", "price_range", "faq_count"]))
