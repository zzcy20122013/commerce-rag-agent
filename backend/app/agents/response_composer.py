from copy import deepcopy

from app.llm.generation import ChatClient, generate_response_composer_result


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


def _as_dict(value: object) -> dict:
    return value if isinstance(value, dict) else {}


def _as_list(value: object) -> list:
    return value if isinstance(value, list) else []
