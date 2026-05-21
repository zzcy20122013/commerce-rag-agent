import json
from collections.abc import Iterator

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from starlette.responses import StreamingResponse

from app.agents.multimodal import run_multimodal_search
from app.agents.graph import run_agent
from app.models.db import get_db, init_db
from app.scripts.seed_products import seed_product_images, seed_products
from app.services.image_service import resolve_upload_path
from app.services.log_service import log_recommendation, log_retrieval
from app.services.session_service import add_message, ensure_session, get_latest_memory


router = APIRouter(prefix="/api/chat", tags=["chat"])


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
    session_memory = payload.memory if payload.memory is not None else get_latest_memory(db, session_id=session.id)
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
        yield sse(
            "message",
            {
                "content": result.get("answer", ""),
                "message_id": assistant_message.id,
                "session_id": session.id,
                "memory": result.get("memory", {}),
            },
        )
        yield sse("trace", result.get("trace", []))
        yield sse("product_cards", result.get("product_cards", []))
        if result.get("comparison"):
            yield sse("comparison", result.get("comparison", {}))
        yield sse("done", {"ok": True})

    return StreamingResponse(event_stream(), media_type="text/event-stream")


def sse(event: str, data: object) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


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
