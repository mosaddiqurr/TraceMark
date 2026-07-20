from __future__ import annotations

from io import BytesIO

import numpy as np
from fastapi.testclient import TestClient
from PIL import Image


def image_bytes() -> bytes:
    rng = np.random.default_rng(20260720)
    values = rng.integers(0, 256, (768, 768, 3), dtype=np.uint8)
    image = Image.fromarray(values, "RGB")
    output = BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()


def register_asset(client: TestClient, csrf: str) -> dict[str, object]:
    response = client.post(
        "/api/v1/assets",
        files={"file": ("fixture.png", image_bytes(), "image/png")},
        headers={"X-CSRF-Token": csrf},
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_health_auth_asset_and_protected_verification(account: tuple[TestClient, str]) -> None:
    client, csrf = account
    assert client.get("/api/v1/health").json()["status"] == "ready"
    asset = register_asset(client, csrf)
    assert asset["name"] == "fixture.png"
    assert asset["perceptual_hashes"]["phash"]

    profiles = client.get("/api/v1/profiles").json()["items"]
    robust = next(profile for profile in profiles if profile["type"] == "robust")
    job = client.post(
        f"/api/v1/assets/{asset['id']}/protect",
        json={"profile_id": robust["id"], "visible_text": None},
        headers={"X-CSRF-Token": csrf},
    )
    assert job.status_code == 200, job.text
    result = job.json()
    assert result["state"] == "completed"
    detail = client.get(f"/api/v1/assets/{asset['id']}")
    assert detail.status_code == 200
    assert len(detail.json()["protected_outputs"]) == 1

    protected = client.get(result["result_url"])
    assert protected.status_code == 200
    evidence = client.post(
        "/api/v1/verification",
        files={"file": ("suspect.png", protected.content, "image/png")},
    )
    assert evidence.status_code == 200, evidence.text
    body = evidence.json()
    assert body["classification"] == "valid_ownership_watermark"
    assert body["watermark"]["valid"] is True
    assert client.get("/api/v1/reports").json()["total"] == 1

    distribution_job = client.post(
        "/api/v1/distributions",
        json={"asset_id": asset["id"], "recipient_label": "Reviewer A", "reference": "R-001"},
        headers={"X-CSRF-Token": csrf},
    )
    assert distribution_job.status_code == 200, distribution_job.text
    distributed = client.get(distribution_job.json()["result_url"])
    traced = client.post("/api/v1/verification", files={"file": ("copy.png", distributed.content, "image/png")})
    assert traced.json()["classification"] == "valid_distribution_watermark"

    collection = client.post("/api/v1/collections", json={"name": "Evidence set"}, headers={"X-CSRF-Token": csrf})
    assert collection.status_code == 200
    collection_id = collection.json()["id"]
    indexed = client.post(
        f"/api/v1/collections/{collection_id}/items",
        files={"file": ("fixture.png", image_bytes(), "image/png")},
        headers={"X-CSRF-Token": csrf},
    )
    assert indexed.status_code == 200, indexed.text
    found = client.post(
        f"/api/v1/collections/{collection_id}/search",
        files={"file": ("query.png", image_bytes(), "image/png")},
    )
    assert found.json()["items"][0]["exact"] is True

    benchmark = client.post(
        "/api/v1/benchmarks", json={"profile": "quick"}, headers={"X-CSRF-Token": csrf}
    )
    assert benchmark.status_code == 200, benchmark.text
    assert client.get("/api/v1/benchmarks").json()["items"][0]["results"]


def test_cross_user_asset_isolation(account: tuple[TestClient, str]) -> None:
    client, csrf = account
    asset = register_asset(client, csrf)
    logout = client.delete("/api/v1/auth/session", headers={"X-CSRF-Token": csrf})
    assert logout.status_code == 204
    other = client.post("/api/v1/auth/register", json={
        "display_name": "Other",
        "email": "other@example.test",
        "password": "another correct battery staple",
    })
    assert other.status_code == 201
    assert client.get(f"/api/v1/assets/{asset['id']}").status_code == 404
    assert client.get(f"/api/v1/assets/{asset['id']}/download").status_code == 404



def test_session_rehydration_is_stable(account: tuple[TestClient, str]) -> None:
    client, _ = account
    first = client.get("/api/v1/auth/session")
    second = client.get("/api/v1/auth/session")
    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["csrf_token"] == second.json()["csrf_token"]