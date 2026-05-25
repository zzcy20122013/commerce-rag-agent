import json
import logging
from collections.abc import Iterator

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from starlette.responses import StreamingResponse

from app.agents.response_composer import attach_response_composer_trace, stream_response_composer_chunks
from app.agents.multimodal import run_multimodal_search
from app.agents.graph import run_agent
from app.models.db import get_db, init_db
from app.scripts.seed_products import seed_product_images, seed_products
from app.services.constraint_parser import merge_exclusions, parse_constraints
from app.services.image_service import resolve_upload_path
from app.services.log_service import log_recommendation, log_retrieval
from app.services.product_service import get_products_by_ids
from app.services.runtime_stats import runtime_stats
from app.services.session_service import add_message, ensure_session, get_latest_memory, update_session_title_from_first_message


router = APIRouter(prefix="/api/chat", tags=["chat"])
logger = logging.getLogger("commerce_rag_agent.sse")


class ChatStreamRequest(BaseModel):
    message: str
    session_id: str | None = None
    memory: dict | None = None
    upload_id: str | None = None


@router.post("/stream")
def chat_stream(payload: ChatStreamRequest, db: Session = Depends(get_db)) -> StreamingResponse:
    init_db()
    seed_products(db)
    seed_product_images(db)
    session = ensure_session(db, session_id=payload.session_id)
    add_message(db, session_id=session.id, role="user", content=payload.message)
    update_session_title_from_first_message(db, session_id=session.id, message=payload.message)
    session_memory = payload.memory if payload.memory is not None else get_latest_memory(db, session_id=session.id)
    constraint_result = parse_constraints(payload.message)
    session_memory = apply_negative_constraints_to_memory(session_memory, constraint_result, db=db)
    if payload.upload_id:
        image_path = resolve_upload_path(payload.upload_id)
        if image_path:
            result = run_multimodal_search(db, query=payload.message, image_path=image_path)
        else:
            result = {
                "intent": "multimodal_search",
                "answer": "我没有找到这张上传图片，请重新上传后再试。",
                "memory": session_memory,
                "retrieved_items": [],
                "product_cards": [],
                "trace": [{"node": "multimodal_search", "error": "upload_not_found"}],
            }
    else:
        result = run_agent(db, payload.message, memory=session_memory)
        if implies_missing_image(payload.message):
            result = {
                **result,
                "intent": "image_text_fallback",
                "answer": (
                    "我还没有收到图片，所以暂时不能按图片外观做相似检索。"
                    "但我可以先根据你文字里提到的预算、品类和使用场景，为你推荐以下几种选择。\n\n"
                    f"{result.get('answer', '')}"
                ),
                "trace": result.get("trace", []) + [
                    {"node": "image_text_fallback", "reason": "image_reference_without_upload"}
                ],
            }
    assistant_message = add_message(
        db,
        session_id=session.id,
        role="assistant",
        content=result.get("answer", ""),
        metadata_json=json.dumps({"memory": result.get("memory", {})}, ensure_ascii=False),
    )
    log_retrieval(
        db,
        session_id=session.id,
        query=payload.message,
        intent=result.get("intent", ""),
        filters=result.get("memory", {}),
        candidates=result.get("retrieved_items", []),
    )
    log_recommendation(
        db,
        session_id=session.id,
        message_id=assistant_message.id,
        products=result.get("product_cards", []),
    )

    def event_stream() -> Iterator[str]:
        nonlocal result
        runtime_stats.sse_opened()
        completed = False
        message_payload_base = {
            "message_id": assistant_message.id,
            "session_id": session.id,
            "memory": result.get("memory", {}),
            "feedback_enabled": should_enable_feedback(result),
        }
        stream_meta: dict = {}
        try:
            for chunk in stream_response_composer_chunks(
                query=payload.message,
                result=result,
                on_complete=stream_meta.update,
            ):
                yield sse("message", {**message_payload_base, "content": chunk})
            result = attach_response_composer_trace(result, stream_meta)
            assistant_message.content = result.get("answer", "")
            assistant_message.metadata_json = json.dumps({"memory": result.get("memory", {})}, ensure_ascii=False)
            db.commit()
            yield sse("trace", result.get("trace", []))
            yield sse("product_cards", result.get("product_cards", []))
            if result.get("comparison"):
                yield sse("comparison", result.get("comparison", {}))
            completed = True
            yield sse("done", {"ok": True})
        except GeneratorExit:
            logger.info("sse_disconnected session_id=%s message_id=%s", session.id, assistant_message.id)
            runtime_stats.sse_disconnected()
            raise
        except Exception as error:
            logger.exception("sse_stream_error session_id=%s message_id=%s", session.id, assistant_message.id)
            runtime_stats.error_seen("SSE_STREAM_ERROR")
            runtime_stats.sse_disconnected()
            yield sse(
                "error",
                {
                    "code": "SSE_STREAM_ERROR",
                    "message": "流式回复中断，请稍后重试",
                    "detail": {"type": type(error).__name__},
                },
            )
        finally:
            if completed:
                runtime_stats.sse_completed()

    return StreamingResponse(event_stream(), media_type="text/event-stream")


def sse(event: str, data: object) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def apply_negative_constraints_to_memory(memory: dict | None, constraint_result: dict, *, db: Session | None = None) -> dict:
    updated = dict(memory or {})
    new_exclusions = resolve_deictic_brand_exclusions(
        updated,
        constraint_result.get("exclusions", []),
        db=db,
    )
    exclusions = merge_exclusions(updated.get("exclusions", []), new_exclusions)
    if exclusions:
        updated["exclusions"] = exclusions
    product_ids = constraint_result.get("exclude_product_ids") or []
    if product_ids:
        updated["exclude_product_ids"] = list(dict.fromkeys(updated.get("exclude_product_ids", []) + product_ids))
    return updated


def resolve_deictic_brand_exclusions(
    memory: dict,
    exclusions: list[dict] | None,
    *,
    db: Session | None = None,
) -> list[dict]:
    if not exclusions or db is None:
        return exclusions or []
    resolved: list[dict] = []
    for item in exclusions:
        if item.get("kind") != "exclude_brand" or not is_deictic_brand_reference(item):
            resolved.append(item)
            continue
        products = get_products_by_ids(db, list(memory.get("last_product_ids", []))[:1])
        if not products or not products[0].brand:
            resolved.append(item)
            continue
        resolved.append({**item, "value": products[0].brand})
    return resolved


def is_deictic_brand_reference(item: dict) -> bool:
    text = f"{item.get('value', '')} {item.get('raw', '')}".strip()
    return any(keyword in text for keyword in ["这个品牌", "这个牌子", "这个", "该品牌", "这牌子", "这品牌"])


def iter_answer_chunks(answer: str, chunk_size: int = 2) -> Iterator[str]:
    text = answer or ""
    if not text:
        yield ""
        return
    for index in range(0, len(text), chunk_size):
        yield text[index:index + chunk_size]


def implies_missing_image(message: str) -> bool:
    lowered = message.lower()
    image_reference_keywords = [
        "这张图",
        "这张图片",
        "图片里",
        "图里",
        "这双鞋",
        "这件",
        "这款",
        "类似这",
        "找类似",
        "同款",
        "similar to this",
        "same style",
    ]
    return any(keyword in lowered for keyword in image_reference_keywords)


def should_enable_feedback(result: dict) -> bool:
    intent = str(result.get("intent", "")).strip().lower()
    if intent in {"chitchat"}:
        return False
    if result.get("product_cards"):
        return True
    return intent in {
        "faq",
        "product_knowledge",
        "product_query",
        "shopping_guide",
        "decision_guide",
        "comparison",
        "multimodal_search",
        "image_text_fallback",
    }
