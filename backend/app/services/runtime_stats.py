from __future__ import annotations

import time
import uuid
from collections import Counter
from threading import Lock
from typing import Callable

from fastapi import FastAPI, Request
from starlette.responses import Response


class RuntimeStats:
    def __init__(self) -> None:
        self._lock = Lock()
        self._started_at = time.time()
        self._requests_total = 0
        self._responses_by_status: Counter[str] = Counter()
        self._errors_by_code: Counter[str] = Counter()
        self._sse_open_total = 0
        self._sse_complete_total = 0
        self._sse_disconnect_total = 0
        self._sse_active = 0

    def request_seen(self) -> None:
        with self._lock:
            self._requests_total += 1

    def response_seen(self, status_code: int) -> None:
        with self._lock:
            self._responses_by_status[str(status_code)] += 1

    def error_seen(self, code: str) -> None:
        with self._lock:
            self._errors_by_code[code] += 1

    def sse_opened(self) -> None:
        with self._lock:
            self._sse_open_total += 1
            self._sse_active += 1

    def sse_completed(self) -> None:
        with self._lock:
            self._sse_complete_total += 1
            self._sse_active = max(0, self._sse_active - 1)

    def sse_disconnected(self) -> None:
        with self._lock:
            self._sse_disconnect_total += 1
            self._sse_active = max(0, self._sse_active - 1)

    def snapshot(self) -> dict:
        with self._lock:
            return {
                "uptime_seconds": round(time.time() - self._started_at, 3),
                "requests_total": self._requests_total,
                "responses_by_status": dict(self._responses_by_status),
                "errors_by_code": dict(self._errors_by_code),
                "sse_open_total": self._sse_open_total,
                "sse_complete_total": self._sse_complete_total,
                "sse_disconnect_total": self._sse_disconnect_total,
                "sse_active": self._sse_active,
            }


runtime_stats = RuntimeStats()


def install_runtime_stats(app: FastAPI, stats: RuntimeStats = runtime_stats) -> None:
    @app.middleware("http")
    async def runtime_stats_middleware(request: Request, call_next: Callable) -> Response:
        request_id = request.headers.get("x-request-id") or f"req_{uuid.uuid4().hex[:12]}"
        request.state.request_id = request_id
        stats.request_seen()
        try:
            response = await call_next(request)
        except Exception:
            stats.response_seen(500)
            raise
        response.headers["x-request-id"] = request_id
        stats.response_seen(response.status_code)
        return response
