"""TraceMark FastAPI application factory."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .database import configure_database, make_engine
from .logging_config import configure_logging
from .middleware import CorrelationIdMiddleware, install_error_handlers
from .ratelimit import RateLimiter
from .routes.api import api_router
from .sessions import MemorySessionBackend, RedisSessionBackend, SessionBackend, SessionManager
from .settings import Settings, load_settings
from .storage import LocalObjectStorage, MinioObjectStorage, ObjectStorage


def _redis_client(settings: Settings) -> Any:
    from redis.asyncio import from_url

    return from_url(  # type: ignore[no-untyped-call]
        settings.redis_url, encoding="utf-8", decode_responses=True
    )


def _storage(settings: Settings) -> ObjectStorage:
    if settings.storage_backend == "minio":
        from minio import Minio

        client = Minio(
            settings.minio_endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            secure=settings.minio_secure,
        )
        storage = MinioObjectStorage(client)
        storage.ensure_buckets()
        return storage
    return LocalObjectStorage(settings.local_storage_root)


def create_app(
    settings: Settings | None = None,
    *,
    session_backend: SessionBackend | None = None,
    storage: ObjectStorage | None = None,
) -> FastAPI:
    settings = (settings or load_settings()).validated()
    configure_logging(settings.log_level)
    engine = make_engine(settings.database_url)
    session_factory = configure_database(engine)
    redis_client = None
    if session_backend is None:
        if settings.session_backend == "memory":
            session_backend = MemorySessionBackend()
        else:
            redis_client = _redis_client(settings)
            session_backend = RedisSessionBackend(redis_client)
    if settings.is_production and isinstance(session_backend, MemorySessionBackend):
        raise ValueError("in-memory sessions are forbidden in production")

    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncIterator[None]:
        yield
        if application.state.redis is not None:
            await application.state.redis.aclose()
        engine.dispose()

    app = FastAPI(
        title="TraceMark API",
        version="0.1.0",
        description="Evidence-oriented still-image watermarking and tracing API",
        lifespan=lifespan,
        docs_url="/api/docs" if not settings.is_production else None,
        redoc_url=None,
    )
    app.state.settings = settings
    app.state.engine = engine
    app.state.session_factory = session_factory
    app.state.redis = redis_client
    app.state.sessions = SessionManager(session_backend, settings.session_pepper, settings.session_ttl_seconds)
    app.state.rate_limiter = RateLimiter(redis_client)
    app.state.storage = storage or _storage(settings)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.allowed_origins),
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type", "X-CSRF-Token", "X-Correlation-ID"],
    )
    app.add_middleware(CorrelationIdMiddleware)
    install_error_handlers(app)

    @app.middleware("http")
    async def security_headers(request: Any, call_next: Any) -> Any:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none'"
        return response

    @app.get("/health/live", include_in_schema=False)
    async def live() -> JSONResponse:
        return JSONResponse({"status": "alive"})

    app.include_router(api_router)
    return app


app = create_app()

