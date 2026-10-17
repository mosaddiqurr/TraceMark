"""A single focused journey; no accounts, crawlers, collections or job resources."""

from __future__ import annotations

import asyncio
import threading
import time
from datetime import UTC, datetime
from typing import Any, Literal
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, Response, UploadFile
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from .. import reports
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


async def _process(request: Request, file: UploadFile, operation: str, *arguments: Any) -> dict[str, Any]:
    settings = request.app.state.settings
    try:
        content = await file.read(settings.max_upload_bytes + 1)
    finally:
        await file.close()
    if len(content) > settings.max_upload_bytes:
        raise HTTPException(413, "The file exceeds the upload size limit.")
    try:
        return await asyncio.to_thread(
            request.app.state.runner.run,
            operation,
            content,
            file.filename or "image",
            file.content_type or "",
            settings,
            *arguments,
        )
    except ProcessingFailure as exc:
        code = {"invalid_image": 422, "processing_timeout": 504, "processing_busy": 503}.get(exc.code, 503)
        raise HTTPException(code, str(exc), headers={"Retry-After": "5"} if code == 503 else None) from exc


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
        "profile": "Balanced invisible · DWT-DCT-QIM v2",
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


@router.post("/verification", dependencies=[Depends(require_csrf)])
async def verify(
    request: Request,
    file: UploadFile = File(...),
    owner: Workspace = Depends(get_workspace),
    session: Session = Depends(get_db),
) -> dict[str, Any]:
    references = [
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
    result = await _process(request, file, "verify", references)
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
