"""Correlation IDs and stable API error responses."""

from __future__ import annotations

import logging
import re
import secrets
from collections.abc import Mapping

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

from .logging_config import correlation_id_var

logger = logging.getLogger(__name__)
_CORRELATION_RE = re.compile(r"^[A-Za-z0-9._-]{1,64}$")


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        supplied = request.headers.get("x-correlation-id", "")
        correlation_id = supplied if _CORRELATION_RE.fullmatch(supplied) else secrets.token_hex(16)
        request.state.correlation_id = correlation_id
        token = correlation_id_var.set(correlation_id)
        try:
            response = await call_next(request)
        finally:
            correlation_id_var.reset(token)
        response.headers["X-Correlation-ID"] = correlation_id
        return response


def _error(
    request: Request, status: int, code: str, message: str, field_errors: Mapping[str, object] | None = None
) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        content={
            "error": {
                "code": code,
                "message": message,
                "field_errors": field_errors or {},
                "correlation_id": getattr(request.state, "correlation_id", "-"),
            }
        },
    )


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(HTTPException)
    async def http_error(request: Request, exc: HTTPException) -> JSONResponse:
        detail = exc.detail if isinstance(exc.detail, str) else "request could not be completed"
        code = {
            400: "bad_request",
            401: "authentication_required",
            403: "forbidden",
            404: "not_found",
            409: "conflict",
            413: "payload_too_large",
            422: "validation_error",
            429: "rate_limited",
        }.get(exc.status_code, "request_failed")
        return _error(request, exc.status_code, code, detail)

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
        fields: dict[str, list[str]] = {}
        for item in exc.errors():
            location = ".".join(str(part) for part in item["loc"] if part != "body") or "request"
            fields.setdefault(location, []).append(str(item["msg"]))
        return _error(request, 422, "validation_error", "request validation failed", fields)

    @app.exception_handler(Exception)
    async def unhandled_error(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("unhandled API error", exc_info=exc)
        return _error(request, 500, "internal_error", "an internal error occurred")

