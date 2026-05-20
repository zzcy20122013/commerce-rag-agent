import os
from typing import Protocol

from dotenv import load_dotenv

from app.llm.deepseek_client import DeepSeekClient
from app.llm.openai_compatible_client import OpenAICompatibleClient


load_dotenv()


class ChatClient(Protocol):
    def chat_sync(self, messages: list[dict[str, str]], *, temperature: float = 0.2) -> str:
        ...


def generate_shopping_answer(
    *,
    query: str,
    cards: list[dict],
    memory: dict,
    fallback: str,
    client: ChatClient | None = None,
) -> str:
    return _generate(
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
    context = "\n".join(hit.get("text", "") for hit in hits)
    return _generate(
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
    if client is None and not _has_provider_key():
        return fallback
    try:
        resolved_client = client or _build_default_client()
        answer = resolved_client.chat_sync(messages, temperature=0.2).strip()
        return answer or fallback
    except Exception:
        return fallback


def _build_default_client() -> ChatClient:
    provider = os.getenv("LLM_PROVIDER", "doubao").lower()
    if provider == "deepseek":
        return DeepSeekClient()
    return OpenAICompatibleClient()


def _has_provider_key() -> bool:
    provider = os.getenv("LLM_PROVIDER", "doubao").lower()
    if provider == "deepseek":
        return bool(os.getenv("DEEPSEEK_API_KEY"))
    return bool(os.getenv("DOUBAO_API_KEY") or os.getenv("ARK_API_KEY"))
