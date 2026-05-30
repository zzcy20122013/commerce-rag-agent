from __future__ import annotations

import asyncio
import logging
import os

from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send


logger = logging.getLogger(__name__)
_semaphore: asyncio.Semaphore | None = None


class ConcurrencyLimitMiddleware:
    def __init__(self, app: ASGIApp, max_concurrent: int | None = None) -> None:
        self.app = app
        self.max_concurrent = max_concurrent

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        sem = await _get_concurrency_semaphore(self.max_concurrent)
        if sem.locked():
            response = JSONResponse(
                status_code=503,
                content={
                    "success": False,
                    "message": "服务繁忙，请稍后重试。",
                    "detail": "concurrency limit reached",
                },
            )
            await response(scope, receive, send)
            return

        async with sem:
            await self.app(scope, receive, send)


class BodySizeLimitMiddleware:
    def __init__(self, app: ASGIApp, max_bytes: int | None = None) -> None:
        self.app = app
        self.max_bytes = max_bytes if max_bytes is not None else _env_int("MAX_BODY_SIZE_MB", 10) * 1024 * 1024

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        content_length = _content_length(scope)
        if content_length > self.max_bytes:
            max_mb = max(self.max_bytes // (1024 * 1024), 1)
            response = JSONResponse(
                status_code=413,
                content={
                    "success": False,
                    "message": f"请求体过大，最大允许 {max_mb} MB。",
                    "detail": f"content-length {content_length} exceeds {self.max_bytes} bytes",
                },
            )
            await response(scope, receive, send)
            return

        await self.app(scope, receive, send)


async def _get_concurrency_semaphore(max_concurrent: int | None = None) -> asyncio.Semaphore:
    global _semaphore
    if _semaphore is None:
        limit = max_concurrent if max_concurrent is not None else _env_int("MAX_CONCURRENT_REQUESTS", 10)
        limit = max(limit, 1)
        _semaphore = asyncio.Semaphore(limit)
        logger.info("concurrency semaphore initialized with limit=%d", limit)
    return _semaphore


def _content_length(scope: Scope) -> int:
    for header_name, header_value in scope.get("headers", []):
        if header_name.lower() != b"content-length":
            continue
        try:
            return int(header_value.decode("ascii"))
        except (ValueError, UnicodeDecodeError):
            return 0
    return 0


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default
