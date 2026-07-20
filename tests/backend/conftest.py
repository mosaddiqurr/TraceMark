from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from tracemark_api.database import Base
from tracemark_api.main import create_app
from tracemark_api.sessions import MemorySessionBackend
from tracemark_api.settings import Settings
from tracemark_api.storage import LocalObjectStorage


@pytest.fixture
def client(tmp_path: Path) -> TestClient:
    settings = Settings(
        environment="test",
        database_url=f"sqlite:///{tmp_path / 'test.db'}",
        redis_url="redis://unused",
        session_pepper="s" * 48,
        allowed_origins=("http://testserver",),
        local_storage_root=tmp_path / "objects",
        storage_backend="local",
        master_key="m" * 48,
        report_key="r" * 48,
    )
    app = create_app(
        settings,
        session_backend=MemorySessionBackend(),
        storage=LocalObjectStorage(settings.local_storage_root),
    )
    Base.metadata.create_all(app.state.engine)
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def account(client: TestClient) -> tuple[TestClient, str]:
    response = client.post("/api/v1/auth/register", json={
        "display_name": "Researcher",
        "email": "owner@example.test",
        "password": "correct horse battery staple",
    })
    assert response.status_code == 201, response.text
    return client, response.json()["csrf_token"]
