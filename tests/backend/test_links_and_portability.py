from __future__ import annotations

import json
from io import BytesIO

from fastapi import HTTPException
from fastapi.testclient import TestClient
from PIL import Image
from test_workflow import image_bytes, protect
from tracemark_api.safe_fetch import FetchResult, SafeFetcher


class FakeFetcher(SafeFetcher):
    """Serves fixed responses so link checks never touch the network."""

    def __init__(self, pages: dict[str, FetchResult]) -> None:
        super().__init__(max_candidates=16)
        self.pages = pages
        self.requested: list[str] = []

    def fetch(self, url: str) -> FetchResult:
        self.requested.append(url)
        if url not in self.pages:
            raise HTTPException(status_code=422, detail="remote source returned HTTP 404")
        return self.pages[url]


def _check(client: TestClient, csrf: str, url: str) -> tuple[int, dict[str, object]]:
    response = client.post("/api/v1/verification/link", json={"url": url}, headers={"X-CSRF-Token": csrf})
    return response.status_code, response.json()


def test_direct_image_link_resolves_the_protected_copy(account: tuple[TestClient, str]) -> None:
    client, csrf = account
    protected = protect(client, csrf, "Client B")
    content = client.get(protected["download_url"]).content
    with Image.open(BytesIO(content)) as image:
        resized = BytesIO()
        image.resize((300, 300), Image.Resampling.LANCZOS).convert("RGB").save(resized, format="JPEG", quality=85)
    url = "https://images.example.test/leak/photo.jpg"
    client.app.state.fetcher = FakeFetcher({url: FetchResult(url, "image/jpeg", resized.getvalue())})

    status, body = _check(client, csrf, url)

    assert status == 200, body
    assert body["kind"] == "image"
    evidence = body["evidence"]
    assert isinstance(evidence, dict)
    assert evidence["verified"] is True
    assert evidence["reference_label"] == "Client B"
    assert evidence["source_url"] == url
    assert evidence["file"]["filename"] == "photo.jpg"
    report = client.get(evidence["report"]["download_url"], params={"format": "pdf"})
    assert report.status_code == 200


def test_page_link_scans_images_and_ranks_the_verified_one_first(account: tuple[TestClient, str]) -> None:
    client, csrf = account
    protected = protect(client, csrf, "Press kit")
    marked = client.get(protected["download_url"]).content
    page = b"""<html><head><meta property="og:image" content="/og.png"></head><body>
        <img src="/unrelated.png"><img data-src="/missing.png">
        <img srcset="/small.png 320w, /marked.png 1200w" src="/small.png"></body></html>"""
    base = "https://news.example.test/story"
    client.app.state.fetcher = FakeFetcher(
        {
            base: FetchResult(base, "text/html", page),
            "https://news.example.test/og.png": FetchResult("https://news.example.test/og.png", "text/plain", b"x"),
            "https://news.example.test/unrelated.png": FetchResult(
                "https://news.example.test/unrelated.png", "image/png", image_bytes(seed=7)
            ),
            "https://news.example.test/marked.png": FetchResult(
                "https://news.example.test/marked.png", "image/png", marked
            ),
        }
    )

    status, body = _check(client, csrf, base)

    assert status == 200, body
    assert body["kind"] == "page"
    images = {item["url"]: item for item in body["images"]}  # type: ignore[union-attr, index]
    assert images["https://news.example.test/marked.png"]["status"] == "verified"
    assert images["https://news.example.test/unrelated.png"]["status"] == "checked"
    assert images["https://news.example.test/og.png"]["status"] == "error"
    assert images["https://news.example.test/missing.png"]["status"] == "error"
    assert body["evidence"]["source_url"] == "https://news.example.test/marked.png"  # type: ignore[index]
    assert body["evidence"]["reference_label"] == "Press kit"  # type: ignore[index]


def test_link_checks_refuse_private_networks_and_pages_without_images(account: tuple[TestClient, str]) -> None:
    client, csrf = account
    status, body = _check(client, csrf, "http://127.0.0.1/admin.png")
    assert status == 422
    assert "non-public" in json.dumps(body)

    empty = "https://empty.example.test/"
    client.app.state.fetcher = FakeFetcher({empty: FetchResult(empty, "text/html", b"<p>No pictures</p>")})
    status, body = _check(client, csrf, empty)
    assert status == 422
    assert "No images" in json.dumps(body)

    assert client.post("/api/v1/verification/link", json={"url": "https://example.test/a.png"}).status_code == 403


def test_trace_export_moves_private_labels_to_another_browser(client: TestClient) -> None:
    first = client.post("/api/v1/workspace").json()["csrf_token"]
    protected = protect(client, first, "Agency X")
    marked = client.get(protected["download_url"]).content
    export = client.get("/api/v1/workspace/export")
    assert export.status_code == 200
    assert export.headers["cache-control"] == "private, no-store"
    document = json.loads(export.content)
    assert document["traces"][0]["reference_label"] == "Agency X"

    client.cookies.clear()
    second = client.post("/api/v1/workspace").json()["csrf_token"]
    unresolved = client.post(
        "/api/v1/verification", files={"file": ("copy.png", marked, "image/png")}, headers={"X-CSRF-Token": second}
    ).json()
    assert unresolved["classification"] == "authenticated_unresolved"

    imported = client.post(
        "/api/v1/workspace/import",
        files={"file": ("records.json", export.content, "application/json")},
        headers={"X-CSRF-Token": second},
    )
    assert imported.json() == {"imported": 1, "skipped": 0}
    again = client.post(
        "/api/v1/workspace/import",
        files={"file": ("records.json", export.content, "application/json")},
        headers={"X-CSRF-Token": second},
    )
    assert again.json() == {"imported": 0, "skipped": 1}
    resolved = client.post(
        "/api/v1/verification", files={"file": ("copy.png", marked, "image/png")}, headers={"X-CSRF-Token": second}
    ).json()
    assert resolved["verified"] is True
    assert resolved["reference_label"] == "Agency X"


def test_tampered_or_foreign_exports_are_rejected(account: tuple[TestClient, str]) -> None:
    client, csrf = account
    protect(client, csrf, "Original")
    document = json.loads(client.get("/api/v1/workspace/export").content)
    document["traces"][0]["reference_label"] = "Forged"
    for content in (json.dumps(document).encode(), b"not json", b'{"kind": "other"}'):
        response = client.post(
            "/api/v1/workspace/import",
            files={"file": ("records.json", content, "application/json")},
            headers={"X-CSRF-Token": csrf},
        )
        assert response.status_code == 422
        assert "Import failed" in response.text


def test_reconfirming_a_workspace_is_not_limited_but_creation_is(client: TestClient) -> None:
    for _ in range(40):
        assert client.post("/api/v1/workspace").status_code == 200
    limited = 0
    for _ in range(35):
        client.cookies.clear()
        limited += client.post("/api/v1/workspace").status_code == 429
    assert limited >= 5
