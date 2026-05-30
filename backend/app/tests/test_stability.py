from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from app.services.error_handlers import install_error_handlers
from app.services.runtime_stats import RuntimeStats, install_runtime_stats
from app.utils.concurrency import BodySizeLimitMiddleware


def test_http_errors_use_unified_error_payload() -> None:
    app = FastAPI()
    stats = RuntimeStats()
    install_runtime_stats(app, stats)
    install_error_handlers(app, stats)

    @app.get("/boom")
    def boom() -> None:
        raise HTTPException(status_code=409, detail={"message": "库存不足", "product_id": "p1"})

    response = TestClient(app).get("/boom")

    assert response.status_code == 409
    payload = response.json()
    assert payload["error"]["code"] == "CONFLICT"
    assert payload["error"]["message"] == "库存不足"
    assert payload["error"]["detail"]["product_id"] == "p1"
    assert payload["error"]["request_id"]


def test_validation_errors_use_unified_error_payload() -> None:
    app = FastAPI()
    stats = RuntimeStats()
    install_runtime_stats(app, stats)
    install_error_handlers(app, stats)

    @app.get("/need-number")
    def need_number(value: int) -> dict:
        return {"value": value}

    response = TestClient(app).get("/need-number?value=abc")

    assert response.status_code == 422
    payload = response.json()
    assert payload["error"]["code"] == "VALIDATION_ERROR"
    assert payload["error"]["message"] == "请求参数格式不正确"
    assert payload["error"]["detail"]["errors"]
    assert payload["error"]["request_id"]
    assert stats.snapshot()["errors_by_code"]["VALIDATION_ERROR"] == 1


def test_runtime_stats_counts_requests_and_errors() -> None:
    app = FastAPI()
    stats = RuntimeStats()
    install_runtime_stats(app, stats)
    install_error_handlers(app, stats)

    @app.get("/ok")
    def ok() -> dict:
        return {"ok": True}

    @app.get("/fail")
    def fail() -> None:
        raise HTTPException(status_code=400, detail="bad request")

    client = TestClient(app)
    assert client.get("/ok").status_code == 200
    assert client.get("/fail").status_code == 400

    snapshot = stats.snapshot()
    assert snapshot["requests_total"] == 2
    assert snapshot["responses_by_status"]["200"] == 1
    assert snapshot["responses_by_status"]["400"] == 1
    assert snapshot["errors_by_code"]["BAD_REQUEST"] == 1


def test_sse_disconnect_stats_are_recorded() -> None:
    stats = RuntimeStats()

    stats.sse_opened()
    stats.sse_disconnected()

    snapshot = stats.snapshot()
    assert snapshot["sse_open_total"] == 1
    assert snapshot["sse_disconnect_total"] == 1
    assert snapshot["sse_active"] == 0


def test_body_size_limit_rejects_large_requests() -> None:
    app = FastAPI()
    app.add_middleware(BodySizeLimitMiddleware, max_bytes=4)

    @app.post("/upload")
    async def upload() -> dict:
        return {"ok": True}

    response = TestClient(app).post("/upload", content=b"12345")

    assert response.status_code == 413
    assert response.json()["success"] is False
