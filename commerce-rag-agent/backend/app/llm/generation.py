import os
from dataclasses import dataclass
from typing import Protocol

import httpx
from dotenv import load_dotenv

from app.llm.openai_compatible_client import OpenAICompatibleClient


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
        messages=[
            {
                "role": "system",
                "content": (
                    "你是专业、克制、可信的电商导购。"
                    "只能基于给定商品卡片和用户约束回答，不编造商品参数。"
                    "回答要简洁，说明筛选逻辑和每个推荐的核心理由。"
                ),
            },
            {
                "role": "user",
                "content": (
                    f"用户问题：{query}\n"
                    f"已提取约束：{memory}\n"
                    f"候选商品卡片：{cards}\n"
                    "请生成一段自然中文导购回答。"
                ),
            },
        ],
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


def generate_faq_result(
    *,
    query: str,
    hits: list[dict],
    fallback: str,
    client: ChatClient | None = None,
) -> GenerationResult:
    context = "\n".join(hit.get("text", "") for hit in hits)
    return _generate_result(
        messages=[
            {
                "role": "system",
                "content": (
                    "你是电商售后与商品知识助手。"
                    "必须基于检索上下文回答；如果上下文不足，要明确说明无法确认。"
                ),
            },
            {
                "role": "user",
                "content": f"用户问题：{query}\n检索上下文：\n{context}\n请给出准确、简洁的回答。",
            },
        ],
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
        return GenerationResult(content=answer, llm_enabled=True)
    except Exception as error:
        return GenerationResult(content=fallback, llm_enabled=False, llm_error=_format_llm_error(error))


def _build_default_client() -> ChatClient:
    return OpenAICompatibleClient()


def _has_provider_key() -> bool:
    return bool(os.getenv("DOUBAO_API_KEY") or os.getenv("ARK_API_KEY"))


def _format_llm_error(error: Exception) -> str:
    if isinstance(error, httpx.HTTPStatusError):
        body = error.response.text.replace("\n", " ")[:500]
        return f"http_{error.response.status_code}: {body}"
    return f"{type(error).__name__}: {str(error)[:500]}"
