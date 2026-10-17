from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from tracemark_api.main import create_app
from tracemark_api.settings import Settings


@pytest.fixture
def client(tmp_path: Path) -> Iterator[TestClient]:
    settings = Settings(
        environment="test",
        data_root=tmp_path / "metadata",
        allowed_origins=("http://testserver",),
        master_key="m" * 48,
        report_key="r" * 48,
        session_pepper="s" * 48,
        processing_rate_limit=1000,
    )
    with TestClient(create_app(settings)) as test_client:
        yield test_client


@pytest.fixture
def account(client: TestClient) -> tuple[TestClient, str]:
    response = client.post("/api/v1/workspace")
    assert response.status_code == 200, response.text
    return client, response.json()["csrf_token"]
