"""Focused still-image Protect / Verify API."""

from __future__ import annotations

import asyncio
import contextlib
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from .database import Base, make_engine, make_session_factory
from .logging_config import configure_logging
from .middleware import BodyLimitMiddleware, CorrelationIdMiddleware, install_error_handlers
from .models import Trace, Workspace
from .ratelimit import RateLimiter
from .routes.api import api_router
from .runner import ProcessingRunner
from .sessions import SessionManager
from .settings import Settings, load_settings
from .transient import TransientStore


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = (settings or load_settings()).validated()
    configure_logging(settings.log_level)
    settings.data_root.mkdir(parents=True, exist_ok=True)
    engine = make_engine(settings.sqlite_url)
    factory = make_session_factory(engine)
    # Two small, versioned tables; no enterprise schema/migration dependencies.
    Base.metadata.create_all(engine)

    async def cleanup(application: FastAPI) -> None:
        while True:
            await asyncio.sleep(30)
            application.state.artifacts.prune()
            await asyncio.to_thread(application.state.sessions.prune)

    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncIterator[None]:
        task = asyncio.create_task(cleanup(application))
        try:
            yield
        finally:
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task
            engine.dispose()

    app = FastAPI(
        title="TraceMark API",
        version="0.2.0",
        lifespan=lifespan,
        docs_url="/api/docs" if not settings.is_production else None,
        redoc_url=None,
        openapi_url="/api/openapi.json" if not settings.is_production else None,
    )
    app.state.settings = settings
    app.state.engine = engine
    app.state.session_factory = factory
    app.state.sessions = SessionManager(
        factory, settings.session_pepper, settings.session_ttl_seconds, settings.max_workspaces
    )
    app.state.rate_limiter = RateLimiter(settings.session_pepper)
    app.state.runner = ProcessingRunner(settings.processing_concurrency, settings.processing_timeout_seconds)
    app.state.artifacts = TransientStore(settings.transient_max_bytes, settings.output_ttl_seconds)
    app.add_middleware(BodyLimitMiddleware, max_bytes=settings.max_upload_bytes + 65536)
    app.add_middleware(CorrelationIdMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.allowed_origins),
        allow_credentials=True,
        allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type", "X-CSRF-Token", "X-Correlation-ID"],
        expose_headers=["Content-Disposition", "X-Correlation-ID", "Retry-After"],
    )
    install_error_handlers(app)
    app.include_router(api_router)

    @app.get("/api/v1/health")
    def health() -> dict[str, str]:
        return {"status": "alive"}

    @app.get("/api/v1/ready")
    def ready() -> dict[str, str]:
        try:
            with factory() as session:
                session.execute(select(Workspace.id).limit(1))
                session.execute(select(Trace.id).limit(1))
        except SQLAlchemyError as exc:
            raise HTTPException(503, "The private trace registry is unavailable.") from exc
        return {"status": "ready", "registry": "available"}

    return app


# Factory mode avoids starting an additional registry in spawned image processors.
# Start with: uvicorn tracemark_api.main:create_app --factory
