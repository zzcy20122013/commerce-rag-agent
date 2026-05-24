from __future__ import annotations

import logging

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.services.runtime_stats import RuntimeStats, runtime_stats


logger = logging.getLogger("commerce_rag_agent.errors")


HTTP_ERROR_CODES = {
    400: "BAD_REQUEST",
    401: "UNAUTHORIZED",
    403: "FORBIDDEN",
    404: "NOT_FOUND",
    409: "CONFLICT",
    422: "VALIDATION_ERROR",
}


def install_error_handlers(app: FastAPI, stats: RuntimeStats = runtime_stats) -> None:
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        code = "VALIDATION_ERROR"
        stats.error_seen(code)
        request_id = getattr(request.state, "request_id", "")
        logger.warning(
            "validation_error code=%s status=422 request_id=%s path=%s",
            code,
            request_id,
            request.url.path,
        )
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": code,
                    "message": "请求参数格式不正确",
                    "detail": {"errors": exc.errors()},
                    "request_id": request_id,
                }
            },
        )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
        code = HTTP_ERROR_CODES.get(exc.status_code, "HTTP_ERROR")
        stats.error_seen(code)
        request_id = getattr(request.state, "request_id", "")
        message, detail = _normalize_detail(exc.detail)
        logger.warning(
            "http_error code=%s status=%s request_id=%s path=%s",
            code,
            exc.status_code,
            request_id,
            request.url.path,
        )
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "code": code,
                    "message": message,
                    "detail": detail,
                    "request_id": request_id,
                }
            },
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        code = "INTERNAL_ERROR"
        stats.error_seen(code)
        request_id = getattr(request.state, "request_id", "")
        logger.exception(
            "unhandled_error code=%s request_id=%s path=%s",
            code,
            request_id,
            request.url.path,
        )
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "code": code,
                    "message": "服务暂时不可用，请稍后再试",
                    "detail": {"type": type(exc).__name__},
                    "request_id": request_id,
                }
            },
        )


def _normalize_detail(detail: object) -> tuple[str, object]:
    if isinstance(detail, dict):
        return str(detail.get("message") or detail.get("detail") or "请求处理失败"), detail
    if detail is None:
        return "请求处理失败", {}
    return str(detail), {"raw": detail}
