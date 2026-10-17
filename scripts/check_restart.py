"""Exercise a real production-configured Uvicorn process across a cold restart."""

from __future__ import annotations

import multiprocessing
import os
import secrets
import socket
import sqlite3
import tempfile
import time
from contextlib import closing
from multiprocessing.process import BaseProcess
from pathlib import Path
from typing import Any, cast

import httpx
import uvicorn

ROOT = Path(__file__).resolve().parents[1]
ORIGIN = "https://images.example.test"


def _serve(environment: dict[str, str], port: int) -> None:
    os.environ.update(environment)
    uvicorn.run(
        "tracemark_api.main:create_app",
        factory=True,
        host="127.0.0.1",
        port=port,
        workers=1,
        access_log=False,
        proxy_headers=False,
        log_level="error",
    )


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def _expect(response: httpx.Response, status: int = 200) -> httpx.Response:
    _require(response.status_code == status, f"Unexpected HTTP status {response.status_code}; expected {status}")
    return response


def _start(environment: dict[str, str], port: int, client: httpx.Client) -> BaseProcess:
    server = multiprocessing.get_context("spawn").Process(target=_serve, args=(environment, port))
    server.start()
    deadline = time.monotonic() + 30
    while server.is_alive() and time.monotonic() < deadline:
        try:
            if client.get("/api/v1/ready", timeout=1).status_code == 200:
                return server
        except httpx.TransportError:
            pass
        time.sleep(0.1)
    _stop(server)
    raise RuntimeError("Native API did not become ready")


def _stop(server: BaseProcess) -> None:
    if server.is_alive():
        server.terminate()
    server.join(10)
    if server.is_alive():
        server.kill()
        server.join(5)
    _require(not server.is_alive(), "Native API process did not stop")


def _counts(database: Path) -> tuple[int, int]:
    with closing(sqlite3.connect(database)) as connection:
        workspaces = connection.execute("SELECT count(*) FROM browser_workspaces").fetchone()[0]
        traces = connection.execute("SELECT count(*) FROM image_traces").fetchone()[0]
    return workspaces, traces


def _protect(client: httpx.Client, sample: bytes) -> tuple[dict[str, Any], bytes]:
    result = cast(
        dict[str, Any],
        _expect(
            client.post(
                "/api/v1/protect",
                files={"file": ("sample.png", sample, "image/png")},
                data={"reference_label": "Restart check"},
            ),
            201,
        ).json(),
    )
    content = _expect(client.get(result["download_url"])).content
    _require(content.startswith(b"\x89PNG\r\n\x1a\n"), "Protected output is not a PNG")
    return result, content


def _verify(client: httpx.Client, result: dict[str, Any], content: bytes) -> dict[str, Any]:
    evidence = cast(
        dict[str, Any],
        _expect(client.post("/api/v1/verification", files={"file": ("protected.png", content, "image/png")})).json(),
    )
    _require(
        evidence["verified"] is True
        and evidence["identifier"] == result["identifier"]
        and evidence["reference_label"] == "Restart check"
        and evidence["watermark"]["authentic"] is True,
        "Saved PNG did not resolve authenticated private evidence",
    )
    report_url = evidence["report"]["download_url"]
    _require(_expect(client.get(report_url)).content.startswith(b"{"), "JSON export failed")
    _require(_expect(client.get(report_url, params={"format": "pdf"})).content.startswith(b"%PDF"), "PDF export failed")
    return evidence


def main() -> None:
    temporary_root = ROOT / ".tmp-tests"
    temporary_root.mkdir(exist_ok=True)
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
    with tempfile.TemporaryDirectory(prefix="restart-", dir=temporary_root) as directory:
        data_root = Path(directory)
        environment = {
            "TRACEMARK_ENV": "production",
            "TRACEMARK_DATA_ROOT": str(data_root),
            "TRACEMARK_ALLOWED_ORIGINS": ORIGIN,
            "TRACEMARK_COOKIE_SECURE": "true",
            "TRACEMARK_COOKIE_SAMESITE": "lax",
            "TRACEMARK_MASTER_KEY": secrets.token_urlsafe(48),
            "TRACEMARK_REPORT_KEY": secrets.token_urlsafe(48),
            "TRACEMARK_SESSION_PEPPER": secrets.token_urlsafe(48),
        }
        with httpx.Client(base_url=f"http://127.0.0.1:{port}", headers={"Origin": ORIGIN}, timeout=45) as client:
            server = _start(environment, port, client)
            try:
                _expect(client.get("/api/docs"), 404)
                workspace = _expect(client.post("/api/v1/workspace"))
                cookie = workspace.headers["set-cookie"]
                _require("Secure" in cookie and "HttpOnly" in cookie, "Production cookie flags missing")
                # This loopback harness represents the HTTPS ingress; browsers use Secure cookies over HTTPS.
                client.headers["Cookie"] = cookie.split(";", 1)[0]
                client.headers["X-CSRF-Token"] = workspace.json()["csrf_token"]
                sample = (ROOT / "apps/web/public/sample.png").read_bytes()
                protected, content = _protect(client, sample)
                evidence = _verify(client, protected, content)
                database = data_root / "registry.sqlite3"
                _require(_counts(database) == (1, 1), "Initial private metadata missing")
                old_pid = server.pid
                _stop(server)
                server = _start(environment, port, client)
                _require(server.pid != old_pid, "Restart reused the original process")
                _require(_counts(database) == (1, 1), "SQLite metadata did not survive restart")
                _expect(client.get(protected["download_url"]), 404)
                _expect(client.get(evidence["report"]["download_url"]), 404)
                resumed = _expect(client.post("/api/v1/workspace")).json()
                _require(resumed["csrf_token"] == workspace.json()["csrf_token"], "Workspace capability lost")
                _verify(client, protected, content)
                repeated, repeated_content = _protect(client, sample)
                _require(repeated["identifier"] != protected["identifier"], "Repeated protection reused identifier")
                _verify(client, repeated, repeated_content)
                _require(_counts(database) == (1, 2), "Repeated protection did not persist metadata")
                _expect(client.delete("/api/v1/workspace"), 204)
                _require(_counts(database) == (0, 0), "Clearing did not delete private metadata")
                _require(
                    all(path.name.startswith("registry.sqlite3") for path in data_root.iterdir()),
                    "Unexpected persisted file in metadata directory",
                )
            finally:
                _stop(server)
    print(
        "PASS: native production startup/restart, SQLite retention, transient expiry, resumed/new Protect/Verify, exports and clear."
    )


if __name__ == "__main__":
    main()
