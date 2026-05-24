from copy import deepcopy
from collections.abc import Callable, Iterator

from app.llm.generation import ChatClient, _format_llm_error, _has_provider_key
from app.llm.generation import generate_response_composer_result
from app.llm.openai_compatible_client import OpenAICompatibleClient
from app.llm.prompt_registry import build_response_composer_messages


def compose_agent_response(
    *,
    query: str,
    result: dict,
    client: ChatClient | None = None,
) -> dict:
    draft_answer = str(result.get("answer") or "").strip()
    if not draft_answer:
        return result
    if str(result.get("intent", "")).strip().lower() in {"purchase_help"}:
        composed = deepcopy(result)
        composed["response_composer"] = {
            "llm_enabled": False,
            "llm_error": None,
        }
        composed["trace"] = list(result.get("trace", [])) + [
            {"node": "response_composer", "llm_enabled": False, "reason": "transactional_answer_preserved"}
        ]
        return composed

    composed = deepcopy(result)
    generation = generate_response_composer_result(
        query=query,
        intent=str(result.get("intent", "")),
        draft_answer=draft_answer,
        memory=_as_dict(result.get("memory")),
        product_cards=_as_list(result.get("product_cards")),
        retrieved_items=_as_list(result.get("retrieved_items")),
        comparison=result.get("comparison") if isinstance(result.get("comparison"), dict) else None,
        fallback=draft_answer,
        client=client,
    )
    composed["answer"] = generation.content
    composed["response_composer"] = {
        "llm_enabled": generation.llm_enabled,
        "llm_error": generation.llm_error,
    }
    trace_item = {"node": "response_composer", "llm_enabled": generation.llm_enabled}
    if generation.llm_error:
        trace_item["llm_error"] = generation.llm_error
    composed["trace"] = list(result.get("trace", [])) + [trace_item]
    return composed


def stream_response_composer_chunks(
    *,
    query: str,
    result: dict,
    client: object | None = None,
    on_complete: Callable[[dict], None] | None = None,
) -> Iterator[str]:
    draft_answer = str(result.get("answer") or "").strip()
    if not draft_answer:
        _complete(on_complete, answer="", llm_enabled=False, llm_error="empty_draft")
        return
    if _should_preserve_answer(result):
        yield from _fallback_chunks(draft_answer)
        _complete(on_complete, answer=draft_answer, llm_enabled=False, llm_error=None, reason="transactional_answer_preserved")
        return
    if client is None and not _has_provider_key():
        yield from _fallback_chunks(draft_answer)
        _complete(on_complete, answer=draft_answer, llm_enabled=False, llm_error="missing_api_key")
        return

    messages = build_response_composer_messages(
        query=query,
        intent=str(result.get("intent", "")),
        draft_answer=draft_answer,
        memory=_as_dict(result.get("memory")),
        product_cards=_as_list(result.get("product_cards")),
        retrieved_items=_as_list(result.get("retrieved_items")),
        comparison=result.get("comparison") if isinstance(result.get("comparison"), dict) else None,
    )
    answer_parts: list[str] = []
    try:
        resolved_client = client or OpenAICompatibleClient()
        for chunk in resolved_client.stream_chat_sync(messages, temperature=0.2):
            if not chunk:
                continue
            answer_parts.append(chunk)
            yield chunk
        answer = "".join(answer_parts).strip()
        if not answer:
            yield from _fallback_chunks(draft_answer)
            _complete(on_complete, answer=draft_answer, llm_enabled=False, llm_error="empty_stream_response")
            return
        _complete(on_complete, answer=answer, llm_enabled=True, llm_error=None)
    except Exception as error:
        yield from _fallback_chunks(draft_answer)
        _complete(on_complete, answer=draft_answer, llm_enabled=False, llm_error=_format_llm_error(error))


def attach_response_composer_trace(result: dict, stream_meta: dict) -> dict:
    composed = deepcopy(result)
    composed["answer"] = stream_meta.get("answer", result.get("answer", ""))
    composed["response_composer"] = {
        "llm_enabled": bool(stream_meta.get("llm_enabled")),
        "llm_error": stream_meta.get("llm_error"),
    }
    trace_item = {"node": "response_composer", "llm_enabled": bool(stream_meta.get("llm_enabled"))}
    if stream_meta.get("reason"):
        trace_item["reason"] = stream_meta["reason"]
    if stream_meta.get("llm_error"):
        trace_item["llm_error"] = stream_meta["llm_error"]
    composed["trace"] = list(result.get("trace", [])) + [trace_item]
    return composed


def _should_preserve_answer(result: dict) -> bool:
    return str(result.get("intent", "")).strip().lower() in {"purchase_help"}


def _fallback_chunks(answer: str) -> Iterator[str]:
    for index in range(0, len(answer), 2):
        yield answer[index:index + 2]


def _complete(
    callback: Callable[[dict], None] | None,
    *,
    answer: str,
    llm_enabled: bool,
    llm_error: str | None,
    reason: str | None = None,
) -> None:
    if callback:
        callback(
            {
                "answer": answer,
                "llm_enabled": llm_enabled,
                "llm_error": llm_error,
                "reason": reason,
            }
        )


def _as_dict(value: object) -> dict:
    return value if isinstance(value, dict) else {}


def _as_list(value: object) -> list:
    return value if isinstance(value, list) else []
