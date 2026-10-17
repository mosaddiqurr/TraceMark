from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import replace
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from starlette.types import Message, Receive, Scope, Send
from tracemark_api import reports
from tracemark_api.logging_config import JsonFormatter, configure_logging
from tracemark_api.middleware import BodyLimitMiddleware
from tracemark_api.settings import Settings
from tracemark_api.transient import TransientStore


def test_readiness_checks_registry_tables_and_returns_a_safe_error(client: TestClient) -> None:
    assert client.get("/api/v1/ready").status_code == 200
    with client.app.state.engine.begin() as connection:
        connection.execute(text("DROP TABLE image_traces"))
    response = client.get("/api/v1/ready")
    assert response.status_code == 503
    assert response.json()["error"]["message"] == "The private trace registry is unavailable."
    assert "SELECT" not in response.text
    assert client.get("/api/v1/health").status_code == 200


def test_exception_logs_omit_sensitive_values_and_uvicorn_tracebacks() -> None:
    private = "SENSITIVE-IMAGE-SESSION-KEY-SENTINEL"
    error = ValueError(private)
    record = logging.LogRecord(
        "uvicorn.error", logging.ERROR, "", 0, "Exception in ASGI application", (), (ValueError, error, None)
    )
    formatted = JsonFormatter().format(record)
    assert private not in formatted
    assert json.loads(formatted)["exception_type"] == "ValueError"
    configure_logging()
    assert all(isinstance(handler.formatter, JsonFormatter) for handler in logging.getLogger("uvicorn.error").handlers)
    assert logging.getLogger("uvicorn.access").disabled


def test_production_configuration_fails_closed() -> None:
    valid = Settings(
        environment="production",
        cookie_secure=True,
        allowed_origins=("https://app.example.test",),
        master_key="m" * 48,
        report_key="r" * 48,
        session_pepper="s" * 48,
    )
    assert valid.validated() is valid
    for change in (
        {"cookie_secure": False},
        {"master_key": "development-master-key-do-not-deploy"},
        {"report_key": valid.master_key},
        {"session_pepper": "short"},
        {"allowed_origins": ("https://*.example.test",)},
        {"allowed_origins": ("http://app.example.test",)},
        {"allowed_origins": ("https://app.example.test/path",)},
        {"database_url": "postgresql://unused"},
    ):
        with pytest.raises(ValueError):
            replace(valid, **change).validated()


def test_private_transient_artifacts_expire_and_remain_bounded(monkeypatch: pytest.MonkeyPatch) -> None:
    owner, foreign = uuid4(), uuid4()
    monkeypatch.setattr("tracemark_api.transient.time.monotonic", lambda: 100.0)
    store = TransientStore(5, 10)
    identifier = store.put(owner, b"12345", "image/png")
    assert store.get(identifier, foreign) is None
    with pytest.raises(RuntimeError):
        store.put(owner, b"x", "image/png")
    monkeypatch.setattr("tracemark_api.transient.time.monotonic", lambda: 111.0)
    assert store.get(identifier, owner) is None
    assert store.get(store.put(owner, b"new", "image/png"), owner) is not None
    store.clear_owner(owner)
    assert not store._items


def test_report_tampering_and_wrong_authentication_are_rejected() -> None:
    key = "r" * 48
    sealed = reports.seal({"verified": False, "identifier": None}, key)
    assert reports.unseal(sealed, key)["verified"] is False
    with pytest.raises(ValueError):
        reports.unseal(sealed, "w" * 48)
    changed = json.loads(sealed)
    changed["verified"] = True
    with pytest.raises(ValueError):
        reports.unseal(json.dumps(changed).encode(), key)
    changed = json.loads(sealed)
    changed["authentication"]["scheme"] = "none"
    with pytest.raises(ValueError):
        reports.unseal(json.dumps(changed).encode(), key)


def test_chunked_body_limit_rejects_before_application_parsing() -> None:
    called = False
    emitted: list[Message] = []
    chunks = iter((b"abc", b"def"))

    async def application(scope: Scope, receive: Receive, send: Send) -> None:
        nonlocal called
        called = True

    async def receive() -> Message:
        return {"type": "http.request", "body": next(chunks), "more_body": True}

    async def send(message: Message) -> None:
        emitted.append(message)

    scope: Scope = {"type": "http", "method": "POST", "headers": [], "path": "/protect"}
    asyncio.run(BodyLimitMiddleware(application, 5)(scope, receive, send))
    assert not called
    assert emitted[0]["status"] == 413
    assert b"abcdef" not in emitted[1]["body"]
