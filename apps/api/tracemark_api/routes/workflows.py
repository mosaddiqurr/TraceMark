"""A single focused journey; no accounts, crawlers, collections or job resources.

Link checks fetch only the one URL a person submits (plus a bounded number of
images on that page) through the DNS-pinned public fetcher.
"""

from __future__ import annotations

import asyncio
import threading
import time
from datetime import UTC, datetime
from typing import Any, Literal
from urllib.parse import unquote, urlsplit
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, Response, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from .. import portability, reports
from ..dependencies import get_db, get_workspace, require_csrf, require_origin
from ..models import Trace, Workspace
from ..runner import ProcessingFailure

router = APIRouter()
_registry_lock = threading.Lock()


def _iso(timestamp: float) -> str:
    return datetime.fromtimestamp(timestamp, UTC).isoformat()


@router.post("/workspace", dependencies=[Depends(require_origin)])
def workspace(request: Request, response: Response) -> dict[str, Any]:
    settings = request.app.state.settings
    existing = request.app.state.sessions.resolve(request.cookies.get(settings.cookie_name))
    if existing is None:
        # Only creation is scarce; every page load re-confirms an existing workspace.
        identity = request.client.host if request.client else "unknown"
        if not request.app.state.rate_limiter.allow(identity, "workspace", 30, 600):
            raise HTTPException(429, "Too many requests. Please try again later.", headers={"Retry-After": "600"})
        try:
            with _registry_lock:
                token, existing = request.app.state.sessions.create()
        except RuntimeError as exc:
            raise HTTPException(503, "Workspace capacity is full. Please try again later.") from exc
        response.set_cookie(
            settings.cookie_name,
            token,
            httponly=True,
            secure=settings.cookie_secure,
            samesite=settings.cookie_samesite,
            max_age=settings.session_ttl_seconds,
            path="/api",
        )
    return {
        "csrf_token": existing.csrf_token,
        "expires_at": _iso(existing.expires_at),
        "limits": {
            "max_upload_bytes": settings.max_upload_bytes,
            "max_image_pixels": settings.max_image_pixels,
            "max_image_dimension": settings.max_image_dimension,
            "output_ttl_seconds": settings.output_ttl_seconds,
            "retention_seconds": settings.session_ttl_seconds,
        },
    }


@router.delete("/workspace", status_code=204, dependencies=[Depends(require_csrf)])
def clear_workspace(
    request: Request, response: Response, owner: Workspace = Depends(get_workspace), session: Session = Depends(get_db)
) -> None:
    session.execute(delete(Workspace).where(Workspace.id == owner.id))
    session.commit()
    request.app.state.artifacts.clear_owner(owner.id)
    response.delete_cookie(
        request.app.state.settings.cookie_name,
        path="/api",
        secure=request.app.state.settings.cookie_secure,
        samesite=request.app.state.settings.cookie_samesite,
    )


async def _run(
    request: Request, content: bytes, filename: str, mime: str, operation: str, *arguments: Any
) -> dict[str, Any]:
    try:
        return await asyncio.to_thread(
            request.app.state.runner.run,
            operation,
            content,
            filename,
            mime,
            request.app.state.settings,
            *arguments,
        )
    except ProcessingFailure as exc:
        code = {"invalid_image": 422, "processing_timeout": 504, "processing_busy": 503}.get(exc.code, 503)
        raise HTTPException(code, str(exc), headers={"Retry-After": "5"} if code == 503 else None) from exc


async def _process(request: Request, file: UploadFile, operation: str, *arguments: Any) -> dict[str, Any]:
    settings = request.app.state.settings
    try:
        content = await file.read(settings.max_upload_bytes + 1)
    finally:
        await file.close()
    if len(content) > settings.max_upload_bytes:
        raise HTTPException(413, "The file exceeds the upload size limit.")
    return await _run(request, content, file.filename or "image", file.content_type or "", operation, *arguments)


@router.post("/protect", status_code=201, dependencies=[Depends(require_csrf)])
async def protect(
    request: Request,
    file: UploadFile = File(...),
    reference_label: str = Form("", max_length=120),
    owner: Workspace = Depends(get_workspace),
    session: Session = Depends(get_db),
) -> dict[str, Any]:
    label = reference_label.strip() or None
    if label and any(ord(character) < 32 for character in label):
        await file.close()
        raise HTTPException(422, "The reference label must be a single line.")
    identifier = uuid4()
    result = await _process(request, file, "protect", str(identifier), bool(label))
    try:
        artifact_id = request.app.state.artifacts.put(owner.id, result["content"], "image/png")
    except RuntimeError as exc:
        raise HTTPException(503, "The download buffer is full. Please try again shortly.") from exc
    try:
        with _registry_lock:
            # Re-check owner expiry/deletion after processing; no orphan trace is persisted.
            active = session.scalar(
                select(Workspace.id).where(Workspace.id == owner.id, Workspace.expires_at > time.time())
            )
            if active is None:
                raise HTTPException(401, "Your workspace expired during processing. Reload and try again.")
            own_count = session.scalar(select(func.count()).select_from(Trace).where(Trace.owner_id == owner.id)) or 0
            total = session.scalar(select(func.count()).select_from(Trace)) or 0
            if (
                own_count >= request.app.state.settings.max_workspace_traces
                or total >= request.app.state.settings.max_traces
            ):
                raise HTTPException(
                    409, "The private trace registry is full. Clear this browser's traces from About to start again."
                )
            trace = Trace(
                id=identifier,
                owner_id=owner.id,
                source_name=result["file"]["filename"],
                reference_label=label,
                payload_type=result["payload_type"],
                source_sha256=result["file"]["sha256"],
                output_sha256=result["output_sha256"],
                descriptor=result["descriptor"],
                created_at=time.time(),
            )
            session.add(trace)
            session.commit()
    except Exception:
        request.app.state.artifacts.discard(artifact_id)
        raise
    return {
        "identifier": str(identifier),
        "reference_label": label,
        "status": "protected",
        "file": result["file"],
        "profile": result["profile"],
        "quality": result["quality"],
        "created_at": _iso(trace.created_at),
        "download_url": f"/api/v1/outputs/{artifact_id}/download",
        "download_expires_at": _iso(time.time() + request.app.state.settings.output_ttl_seconds),
        "trace_expires_at": _iso(owner.expires_at),
    }


@router.get("/outputs/{output_id}/download")
def download_output(output_id: UUID, request: Request, owner: Workspace = Depends(get_workspace)) -> Response:
    artifact = request.app.state.artifacts.get(output_id, owner.id)
    if artifact is None or artifact.mime_type != "image/png":
        raise HTTPException(404, "The protected image is unavailable or its download window has expired.")
    return Response(
        artifact.content,
        media_type="image/png",
        headers={"Content-Disposition": 'attachment; filename="tracemark-protected.png"'},
    )


def _references(request: Request, owner: Workspace, session: Session) -> list[dict[str, Any]]:
    return [
        {
            "id": str(row.id),
            "source_name": row.source_name,
            "reference_label": row.reference_label,
            "payload_type": row.payload_type,
            "source_sha256": row.source_sha256,
            "output_sha256": row.output_sha256,
            "descriptor": row.descriptor,
            "protected_at": _iso(row.created_at),
        }
        for row in session.scalars(
            select(Trace).where(Trace.owner_id == owner.id).limit(request.app.state.settings.max_workspace_traces)
        )
    ]


def _sealed(request: Request, owner: Workspace, session: Session, result: dict[str, Any]) -> dict[str, Any]:
    # A concurrent workspace deletion must also invalidate in-flight evidence.
    session.expire_all()
    if session.scalar(select(Workspace.id).where(Workspace.id == owner.id, Workspace.expires_at > time.time())) is None:
        raise HTTPException(401, "Your workspace expired during verification. Reload and try again.")
    result.update({"id": str(uuid4()), "created_at": _iso(time.time())})
    snapshot = reports.seal(result, request.app.state.settings.report_key)
    try:
        report_id = request.app.state.artifacts.put(owner.id, snapshot, "application/json")
    except RuntimeError as exc:
        raise HTTPException(503, "The report buffer is full. Please try again shortly.") from exc
    result["report"] = {
        "download_url": f"/api/v1/reports/{report_id}/download",
        "expires_at": _iso(time.time() + request.app.state.settings.output_ttl_seconds),
    }
    return result


@router.post("/verification", dependencies=[Depends(require_csrf)])
async def verify(
    request: Request,
    file: UploadFile = File(...),
    owner: Workspace = Depends(get_workspace),
    session: Session = Depends(get_db),
) -> dict[str, Any]:
    result = await _process(request, file, "verify", _references(request, owner, session))
    return _sealed(request, owner, session, result)


class LinkCheck(BaseModel):
    url: str = Field(min_length=8, max_length=2048)


_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}
# Strongest evidence first; the best image on a page becomes the full result.
_RANKING = (
    "valid_distribution_watermark",
    "valid_ownership_watermark",
    "authenticated_unresolved",
    "invalid_authenticated_payload",
    "exact_registered_hash",
    "possible_visual_match",
    "no_evidence",
)


def _link_filename(url: str) -> str:
    name = unquote(urlsplit(url).path.rstrip("/").rsplit("/", 1)[-1])
    return name[:120] or "linked-image"


@router.post("/verification/link", dependencies=[Depends(require_csrf)])
async def verify_link(
    request: Request,
    body: LinkCheck,
    owner: Workspace = Depends(get_workspace),
    session: Session = Depends(get_db),
) -> dict[str, Any]:
    settings = request.app.state.settings
    if not settings.link_checks_enabled:
        raise HTTPException(404, "Link checks are disabled on this deployment.")
    fetcher = request.app.state.fetcher
    deadline = time.monotonic() + settings.link_check_seconds
    try:
        first = await asyncio.to_thread(fetcher.fetch, body.url.strip())
    except HTTPException as exc:
        raise HTTPException(422, f"The link could not be checked: {exc.detail}.") from exc
    if first.content_type in _IMAGE_TYPES:
        kind, candidates = "image", [first.final_url]
    else:
        try:
            candidates = fetcher.page_image_urls(first)
        except HTTPException as exc:
            raise HTTPException(422, f"The link could not be checked: {exc.detail}.") from exc
        kind = "page"
        if not candidates:
            raise HTTPException(422, "No images were found on that page. Try a direct image link.")
    references = _references(request, owner, session)
    images: list[dict[str, Any]] = []
    best: tuple[int, str, dict[str, Any]] | None = None
    truncated = False
    for image_url in candidates[: settings.link_check_max_images]:
        if time.monotonic() > deadline:
            truncated = True
            break
        try:
            fetched = first if kind == "image" else await asyncio.to_thread(fetcher.fetch, image_url)
            if fetched.content_type not in _IMAGE_TYPES:
                raise HTTPException(422, "not a JPEG, PNG or WebP image")
            result = await _run(
                request, fetched.body, _link_filename(fetched.final_url), fetched.content_type, "verify", references
            )
        except HTTPException as exc:
            images.append({"url": image_url, "status": "error", "message": str(exc.detail)})
            continue
        rank = _RANKING.index(result["classification"]) if result["classification"] in _RANKING else len(_RANKING)
        images.append(
            {
                "url": image_url,
                "status": "verified" if result["verified"] else "checked",
                "classification": result["classification"],
                "reference_label": result["reference_label"],
                "identifier": result["identifier"],
            }
        )
        if best is None or rank < best[0]:
            best = (rank, image_url, result)
    truncated = truncated or len(candidates) > settings.link_check_max_images
    evidence = None
    if best is not None:
        evidence = _sealed(request, owner, session, {**best[2], "source_url": best[1]})
    return {
        "source_url": first.final_url,
        "kind": kind,
        "images": images,
        "truncated": truncated,
        "evidence": evidence,
    }


@router.get("/workspace/export")
def export_traces(
    request: Request, owner: Workspace = Depends(get_workspace), session: Session = Depends(get_db)
) -> Response:
    traces = [
        {
            "id": str(row.id),
            "source_name": row.source_name,
            "reference_label": row.reference_label,
            "payload_type": row.payload_type,
            "source_sha256": row.source_sha256,
            "output_sha256": row.output_sha256,
            "descriptor": row.descriptor,
            "created_at": row.created_at,
        }
        for row in session.scalars(select(Trace).where(Trace.owner_id == owner.id).order_by(Trace.created_at))
    ]
    content = portability.seal(traces, _iso(time.time()), request.app.state.settings.report_key)
    return Response(
        content,
        media_type="application/json",
        headers={"Content-Disposition": 'attachment; filename="tracemark-trace-records.json"'},
    )


@router.post("/workspace/import", dependencies=[Depends(require_csrf)])
async def import_traces(
    request: Request,
    file: UploadFile = File(...),
    owner: Workspace = Depends(get_workspace),
    session: Session = Depends(get_db),
) -> dict[str, int]:
    settings = request.app.state.settings
    try:
        content = await file.read(portability.MAX_EXPORT_BYTES + 1)
    finally:
        await file.close()
    try:
        records = portability.unseal(content, settings.report_key)
    except portability.ImportRejected as exc:
        raise HTTPException(422, f"Import failed: {exc}.") from exc
    imported = skipped = 0
    with _registry_lock:
        own_count = session.scalar(select(func.count()).select_from(Trace).where(Trace.owner_id == owner.id)) or 0
        total = session.scalar(select(func.count()).select_from(Trace)) or 0
        for record in records:
            identifier = UUID(record["id"])
            existing = session.get(Trace, identifier)
            if existing is not None and existing.owner_id == owner.id:
                skipped += 1
                continue
            if own_count >= settings.max_workspace_traces or (existing is None and total >= settings.max_traces):
                raise HTTPException(409, "The private trace registry is full. Clear traces from About and retry.")
            if existing is not None:
                # The signed export is the owner's credential; importing moves the record here.
                existing.owner_id = owner.id
            else:
                session.add(Trace(**{**record, "id": identifier, "owner_id": owner.id}))
                total += 1
            own_count += 1
            imported += 1
        session.commit()
    return {"imported": imported, "skipped": skipped}


@router.get("/reports/{report_id}/download")
def download_report(
    report_id: UUID,
    request: Request,
    format: Literal["json", "pdf"] = "json",
    owner: Workspace = Depends(get_workspace),
) -> Response:
    artifact = request.app.state.artifacts.get(report_id, owner.id)
    if artifact is None or artifact.mime_type != "application/json":
        raise HTTPException(404, "The report is unavailable or its download window has expired.")
    try:
        snapshot = reports.unseal(artifact.content, request.app.state.settings.report_key)
    except (KeyError, ValueError, TypeError, AttributeError) as exc:
        raise HTTPException(409, "Report integrity validation failed.") from exc
    content = artifact.content if format == "json" else reports.pdf(snapshot)
    return Response(
        content,
        media_type="application/json" if format == "json" else "application/pdf",
        headers={"Content-Disposition": f'attachment; filename="tracemark-verification-report.{format}"'},
    )
