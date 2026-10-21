"""Bounded bodies, abuse control, correlation IDs and input-safe errors."""

from __future__ import annotations

import asyncio
import logging
import re
import secrets

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from .logging_config import correlation_id_var

logger = logging.getLogger(__name__)
_CORRELATION_RE = re.compile(r"^[A-Za-z0-9._-]{1,64}$")


class BodyLimitMiddleware:
    """Cap actual bytes, including chunked bodies, before multipart spooling."""

    def __init__(self, app: ASGIApp, max_bytes: int):
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope["method"] in {"GET", "HEAD", "OPTIONS"}:
            await self.app(scope, receive, send)
            return
        headers = dict(scope["headers"])
        try:
            length = int(headers.get(b"content-length", b"0"))
            if length < 0:
                raise ValueError
        except ValueError:
            await JSONResponse(
                {"error": {"code": "bad_request", "message": "Invalid request length."}}, status_code=400
            )(scope, receive, send)
            return
        if length > self.max_bytes:
            await self.reject(scope, receive, send)
            return
        data = bytearray()
        try:
            async with asyncio.timeout(30):
                while True:
                    message = await receive()
                    if message["type"] == "http.disconnect":
                        return
                    data.extend(message.get("body", b""))
                    if len(data) > self.max_bytes:
                        await self.reject(scope, receive, send)
                        return
                    if not message.get("more_body", False):
                        break
        except TimeoutError:
            await JSONResponse(
                {"error": {"code": "request_timeout", "message": "Upload took too long."}}, status_code=408
            )(scope, receive, send)
            return
        delivered = False

        async def replay() -> Message:
            nonlocal delivered
            if delivered:
                return await receive()
            delivered = True
            return {"type": "http.request", "body": bytes(data), "more_body": False}

        await self.app(scope, replay, send)

    @staticmethod
    async def reject(scope: Scope, receive: Receive, send: Send) -> None:
        await JSONResponse(
            {"error": {"code": "payload_too_large", "message": "The file exceeds the upload size limit."}},
            status_code=413,
        )(scope, receive, send)


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        supplied = request.headers.get("x-correlation-id", "")
        correlation_id = supplied if _CORRELATION_RE.fullmatch(supplied) else secrets.token_hex(16)
        request.state.correlation_id = correlation_id
        token = correlation_id_var.set(correlation_id)
        try:
            settings = request.app.state.settings
            limiter = request.app.state.rate_limiter
            identity = request.client.host if request.client else "unknown"
            if request.url.path.endswith("/verification/link"):
                allowed = limiter.allow(identity, "link_checks", settings.link_check_rate_limit, 600)
            elif request.url.path.endswith(("/protect", "/verification")):
                allowed = limiter.allow(identity, "processing", settings.processing_rate_limit, 600)
            else:
                allowed = limiter.allow(identity, "requests", 240, 60)
            if not allowed:
                response: Response = _error(request, 429, "rate_limited", "Too many requests. Please try again later.")
                response.headers["Retry-After"] = "600"
            else:
                response = await call_next(request)
        finally:
            correlation_id_var.reset(token)
        response.headers.update(
            {
                "X-Correlation-ID": correlation_id,
                "X-Content-Type-Options": "nosniff",
                "X-Frame-Options": "DENY",
                "Referrer-Policy": "no-referrer",
                "Cache-Control": "private, no-store",
                "Content-Security-Policy": "default-src 'none'; frame-ancestors 'none'",
            }
        )
        return response


def _error(request: Request, status: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        content={
            "error": {
                "code": code,
                "message": message,
                "correlation_id": getattr(request.state, "correlation_id", "-"),
            }
        },
    )


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(HTTPException)
    async def http_error(request: Request, exc: HTTPException) -> JSONResponse:
        code = {
            400: "bad_request",
            401: "workspace_required",
            403: "forbidden",
            404: "not_found",
            409: "conflict",
            413: "payload_too_large",
            422: "validation_error",
            429: "rate_limited",
            503: "unavailable",
            504: "processing_timeout",
        }.get(exc.status_code, "request_failed")
        response = _error(request, exc.status_code, code, str(exc.detail))
        if exc.headers:
            response.headers.update(exc.headers)
        return response

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
        del exc
        return _error(request, 422, "validation_error", "Check the image and reference field, then try again.")

    @app.exception_handler(Exception)
    async def unhandled_error(request: Request, exc: Exception) -> JSONResponse:
        logger.error("API operation failed (%s)", type(exc).__name__)
        return _error(request, 500, "internal_error", "The request could not be completed safely.")
