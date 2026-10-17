"""Real isolated API for browser acceptance, using deterministic test-only keys."""

from pathlib import Path

from fastapi import FastAPI
from tracemark_api.main import create_app as application_factory
from tracemark_api.settings import Settings


def create_app() -> FastAPI:
    return application_factory(
        Settings(
            environment="test",
            data_root=Path(".tmp-tests/e2e-registry"),
            allowed_origins=("http://127.0.0.1:5184", "http://localhost:5184"),
            master_key="browser-test-master-key-2026-10-04",
            report_key="browser-test-report-key-2026-10-04",
            session_pepper="browser-test-session-key-2026-10-04",
            processing_rate_limit=1000,
        )
    )
