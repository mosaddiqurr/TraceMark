from __future__ import annotations

import multiprocessing
import time
from io import BytesIO
from unittest.mock import patch
from uuid import UUID, uuid4

import numpy as np
import pytest
from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy import func, select
from tracemark_api.models import Trace, Workspace
from tracemark_api.runner import ProcessingRunner
from tracemark_watermark import PayloadType, RobustWatermarkEngine, WatermarkPayload, encode_payload
from tracemark_watermark.payload import _deinterleave, _interleave


def image_bytes(seed: int = 20260720) -> bytes:
    rng = np.random.default_rng(seed)
    y, x = np.indices((512, 512))
    noise = rng.integers(0, 32, size=(512, 512), dtype=np.uint8)
    values = np.empty((512, 512, 3), dtype=np.uint8)
    values[..., 0] = (x // 2 + y // 3 + noise) % 256
    values[..., 1] = (x // 5 + y // 2 + noise // 2) % 256
    values[..., 2] = (x // 3 + y // 7 + noise) % 256
    output = BytesIO()
    Image.fromarray(values).save(output, format="PNG")
    return output.getvalue()


def protect(client: TestClient, csrf: str, label: str = "") -> dict[str, object]:
    response = client.post(
        "/api/v1/protect",
        files={"file": ("../../fixture.png", image_bytes(), "image/png")},
        data={"reference_label": label},
        headers={"X-CSRF-Token": csrf},
    )
    assert response.status_code == 201, response.text
    return response.json()


def verify(client: TestClient, csrf: str, data: bytes, mime: str = "image/png") -> dict[str, object]:
    response = client.post(
        "/api/v1/verification", files={"file": ("candidate", data, mime)}, headers={"X-CSRF-Token": csrf}
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_complete_protection_distribution_and_verification_journey(account: tuple[TestClient, str]) -> None:
    client, csrf = account
    protected = protect(client, csrf, "Reviewer A / CASE-001")
    assert protected["status"] == "protected"
    assert protected["reference_label"] == "Reviewer A / CASE-001"
    downloaded = client.get(protected["download_url"])
    assert downloaded.status_code == 200
    assert downloaded.content.startswith(b"\x89PNG\r\n\x1a\n")
    assert downloaded.headers["cache-control"] == "private, no-store"
    assert downloaded.headers["content-disposition"] == 'attachment; filename="tracemark-protected.png"'
    with Image.open(BytesIO(downloaded.content)) as decoded:
        decoded.verify()
    assert client.get(protected["download_url"]).content == downloaded.content
    evidence = verify(client, csrf, downloaded.content)
    assert evidence["verified"] is True
    assert evidence["classification"] == "valid_distribution_watermark"
    assert evidence["identifier"] == protected["identifier"]
    assert evidence["reference_label"] == "Reviewer A / CASE-001"
    assert evidence["source_filename"] == "fixture.png"
    assert evidence["exact_hash"] == {"matched": True, "kind": "protected_copy"}
    assert evidence["watermark"]["authentic"] is True
    assert evidence["watermark"]["integrity_state"] == "valid"
    assert evidence["visual"]["orb_match_count"] > 0
    assert evidence["visual"]["ransac_inliers"] > 0
    for format_name, mime, prefix in (("json", "application/json", b"{"), ("pdf", "application/pdf", b"%PDF")):
        report = client.get(evidence["report"]["download_url"], params={"format": format_name})
        assert report.status_code == 200
        assert report.headers["content-type"].startswith(mime)
        assert report.content.startswith(prefix)
        assert report.headers["content-disposition"].endswith(f'.{format_name}"')
    assert client.get(evidence["report"]["download_url"], params={"format": "html"}).status_code == 422
    assert client.get(f"/api/v1/outputs/{uuid4()}/download").status_code == 404
    with client.app.state.session_factory() as session:
        row = session.get(Trace, UUID(protected["identifier"]))
        assert row is not None
        assert "descriptors" in row.descriptor
        assert row.source_name == "fixture.png"
    assert not list(client.app.state.settings.data_root.rglob("*.png"))


def test_ownership_exact_source_and_altered_image_have_separate_evidence(account: tuple[TestClient, str]) -> None:
    client, csrf = account
    protected = protect(client, csrf)
    content = client.get(protected["download_url"]).content
    clean = verify(client, csrf, content)
    assert clean["classification"] == "valid_ownership_watermark"
    assert clean["reference_label"] is None
    exact_source = verify(client, csrf, image_bytes())
    assert exact_source["verified"] is False
    assert exact_source["classification"] == "exact_registered_hash"
    assert exact_source["exact_hash"]["kind"] == "source"
    with Image.open(BytesIO(content)) as image:
        recompressed = BytesIO()
        image.save(recompressed, format="JPEG", quality=95, subsampling=0)
        resized = BytesIO()
        image.resize((384, 384), Image.Resampling.LANCZOS).save(resized, format="PNG")
    jpeg = verify(client, csrf, recompressed.getvalue(), "image/jpeg")
    assert jpeg["verified"] is True
    assert jpeg["exact_hash"]["matched"] is False
    resize = verify(client, csrf, resized.getvalue())
    assert resize["verified"] is False
    assert resize["classification"] == "possible_visual_match"


def test_wrong_key_forged_payload_and_unregistered_token_are_never_accepted(account: tuple[TestClient, str]) -> None:
    client, csrf = account
    protected = protect(client, csrf)
    content = client.get(protected["download_url"]).content
    settings = client.app.state.settings
    original_key = settings.master_key
    object.__setattr__(settings, "master_key", "w" * 48)
    try:
        wrong_key = verify(client, csrf, content)
    finally:
        object.__setattr__(settings, "master_key", original_key)
    assert wrong_key["verified"] is False
    assert wrong_key["watermark"]["authentic"] is False
    source = Image.open(BytesIO(image_bytes()))
    master = original_key.encode()
    payload = WatermarkPayload(PayloadType.OWNERSHIP, 2, 1, uuid4().bytes)
    wrong = b"f" * 48
    forged_codeword = _interleave(_deinterleave(encode_payload(payload, wrong), wrong, 1), master, 1)
    with patch("tracemark_watermark.robust.encode_payload", return_value=forged_codeword):
        forged_image = RobustWatermarkEngine().embed(source, payload, master).image
    forged = BytesIO()
    forged_image.save(forged, format="PNG")
    result = verify(client, csrf, forged.getvalue())
    assert result["classification"] == "invalid_authenticated_payload"
    assert result["watermark"]["authentic"] is False
    assert result["identifier"] is None
    unknown = BytesIO()
    RobustWatermarkEngine().embed(source, payload, master).image.save(unknown, format="PNG")
    unresolved = verify(client, csrf, unknown.getvalue())
    assert unresolved["verified"] is False
    assert unresolved["classification"] == "authenticated_unresolved"
    assert unresolved["identifier"] is None


def test_cross_workspace_downloads_reports_and_labels_stay_private(account: tuple[TestClient, str]) -> None:
    client, csrf = account
    protected = protect(client, csrf, "PRIVATE-LABEL")
    content = client.get(protected["download_url"]).content
    evidence = verify(client, csrf, content)
    cookie = client.cookies.get("tracemark_workspace")
    client.cookies.clear()
    other = client.post("/api/v1/workspace")
    assert other.status_code == 200
    other_csrf = other.json()["csrf_token"]
    assert client.get(protected["download_url"]).status_code == 404
    assert client.get(evidence["report"]["download_url"]).status_code == 404
    foreign = verify(client, other_csrf, content)
    assert foreign["verified"] is False
    assert foreign["identifier"] is None
    assert foreign["reference_label"] is None
    assert "PRIVATE-LABEL" not in str(foreign)
    client.cookies.clear()
    client.cookies.set("tracemark_workspace", cookie, domain="testserver.local", path="/api")
    assert client.get(protected["download_url"]).status_code == 200
    assert client.delete("/api/v1/workspace", headers={"X-CSRF-Token": csrf}).status_code == 204
    with client.app.state.session_factory() as session:
        assert session.scalar(select(func.count()).select_from(Trace)) == 0
    assert client.get(protected["download_url"]).status_code == 401


def test_workspace_rehydration_expiry_and_registry_restart(account: tuple[TestClient, str]) -> None:
    client, csrf = account
    assert client.post("/api/v1/workspace").json()["csrf_token"] == csrf
    manager = client.app.state.sessions
    assert manager.resolve(client.cookies.get("tracemark_workspace")) is not None
    with client.app.state.session_factory() as session:
        row = session.scalar(select(Workspace))
        assert row is not None
        assert row.token_digest != client.cookies.get("tracemark_workspace")
        row.expires_at = time.time() - 1
        session.commit()
    assert client.delete("/api/v1/workspace", headers={"X-CSRF-Token": csrf}).status_code == 401
    manager.prune()
    with client.app.state.session_factory() as session:
        assert session.scalar(select(func.count()).select_from(Workspace)) == 0


def test_csrf_origin_cors_and_safe_missing_routes(account: tuple[TestClient, str]) -> None:
    client, csrf = account
    data = {"file": ("image.png", image_bytes(), "image/png")}
    assert client.post("/api/v1/protect", files=data).status_code == 403
    assert client.post("/api/v1/verification", files=data, headers={"X-CSRF-Token": "wrong"}).status_code == 403
    assert client.post("/api/v1/workspace", headers={"Origin": "https://evil.test"}).status_code == 403
    preflight = client.options(
        "/api/v1/protect", headers={"Origin": "http://testserver", "Access-Control-Request-Method": "POST"}
    )
    assert preflight.status_code == 200
    assert preflight.headers["access-control-allow-origin"] == "http://testserver"
    cors = client.get("/api/v1/health", headers={"Origin": "https://evil.test"})
    assert "access-control-allow-origin" not in cors.headers
    assert (
        "Content-Disposition" in preflight.headers.get("access-control-expose-headers", "")
        or "Content-Disposition"
        in client.get("/api/v1/health", headers={"Origin": "http://testserver"}).headers[
            "access-control-expose-headers"
        ]
    )
    assert client.get("/api/v1/ready").json()["status"] == "ready"
    for path in (
        "/api/v1/auth/login",
        "/api/v1/collections",
        "/api/v1/scans",
        "/api/v1/jobs",
        "/api/v1/system/dashboard",
    ):
        assert client.get(path).status_code == 404


@pytest.mark.parametrize(
    ("payload", "mime"),
    [(b"not an image", "image/png"), (b"\x89PNG\r\n\x1a\ncorrupted", "image/png"), (image_bytes(), "image/jpeg")],
    ids=("unsupported", "corrupt", "mismatched-mime"),
)
def test_invalid_corrupt_and_mismatched_images_are_rejected(
    account: tuple[TestClient, str], payload: bytes, mime: str
) -> None:
    client, csrf = account
    response = client.post(
        "/api/v1/protect", files={"file": ("invalid.png", payload, mime)}, headers={"X-CSRF-Token": csrf}
    )
    assert response.status_code == 422
    assert "Traceback" not in response.text


def test_size_dimension_animation_timeout_and_rate_limits(account: tuple[TestClient, str]) -> None:
    client, csrf = account
    oversized = client.post("/api/v1/protect", content=b"x", headers={"Content-Length": str(100 * 1024 * 1024)})
    assert oversized.status_code == 413
    small = BytesIO()
    Image.new("RGB", (32, 32), "blue").save(small, format="PNG")
    rejected = client.post(
        "/api/v1/protect", files={"file": ("small.png", small.getvalue(), "image/png")}, headers={"X-CSRF-Token": csrf}
    )
    assert rejected.status_code == 422
    children_before = {p.pid for p in multiprocessing.active_children()}
    client.app.state.runner = ProcessingRunner(1, 0.001)
    started = time.monotonic()
    timed_out = client.post(
        "/api/v1/verification",
        files={"file": ("image.png", image_bytes(), "image/png")},
        headers={"X-CSRF-Token": csrf},
    )
    assert timed_out.status_code == 504
    assert time.monotonic() - started < 5
    assert {p.pid for p in multiprocessing.active_children()} == children_before
    retry = client.post(
        "/api/v1/verification",
        files={"file": ("image.png", image_bytes(), "image/png")},
        headers={"X-CSRF-Token": csrf},
    )
    assert retry.status_code == 504  # Timeout releases admission for the next request.
    limiter = client.app.state.rate_limiter
    assert limiter.allow("fixture", "rate-test", 1, 60)
    assert not limiter.allow("fixture", "rate-test", 1, 60)
    object.__setattr__(client.app.state.settings, "processing_rate_limit", 1)
    assert (
        client.post(
            "/api/v1/protect", files={"file": ("image.png", image_bytes(), "image/png")}, headers={"X-CSRF-Token": csrf}
        ).status_code
        == 429
    )
