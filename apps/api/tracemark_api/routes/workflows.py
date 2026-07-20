"""Real v1 product workflows built on the standalone forensic engine."""

from __future__ import annotations

import hmac
import json
import logging
import secrets
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from hashlib import sha256
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from time import perf_counter
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from fastapi.responses import Response
from PIL import Image
from pydantic import BaseModel, Field, HttpUrl
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session
from tracemark_watermark import (
    C2PAProvenanceAdapter,
    CapacityError,
    LSBWatermarkEngine,
    PayloadType,
    RobustWatermarkEngine,
    VisibleWatermarkOptions,
    WatermarkPayload,
    add_visible_text,
    fingerprint,
    hamming_distance,
    measure_quality,
)

from ..database import get_db
from ..dependencies import get_current_user, require_csrf
from ..enums import EvidenceClassification, IntegrityState, JobState, ProvenanceState
from ..models import (
    Asset,
    BenchmarkResult,
    BenchmarkRun,
    Collection,
    DistributionCopy,
    IndexedMedia,
    Job,
    ProtectedOutput,
    Report,
    ScanSource,
    User,
    VerificationEvidence,
)
from ..scoping import get_owned
from ..storage import new_object_key
from ..uploads import UploadRejected, validate_image, validated_zip_images

logger = logging.getLogger(__name__)

router = APIRouter()
PROFILE_IDS = {
    UUID("10000000-0000-4000-8000-000000000001"): ("Balanced robust", "robust", 32.0),
    UUID("10000000-0000-4000-8000-000000000002"): ("High robustness", "robust", 42.0),
    UUID("10000000-0000-4000-8000-000000000003"): ("Educational LSB", "lsb", 0.0),
}


class ProtectRequest(BaseModel):
    profile_id: UUID
    visible_text: str | None = Field(default=None, max_length=120)


class DistributionRequest(BaseModel):
    asset_id: UUID
    recipient_label: str = Field(min_length=1, max_length=120)
    reference: str | None = Field(default=None, max_length=120)


class CollectionRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)


class ScanRequest(BaseModel):
    url: HttpUrl


class BenchmarkRequest(BaseModel):
    profile: str = Field(pattern="^(quick|standard|aggressive)$")


def _page(items: Sequence[Mapping[str, object]]) -> dict[str, object]:
    return {"items": items, "total": len(items), "next_cursor": None}


def _key(request: Request) -> bytes:
    value = str(request.app.state.settings.master_key).encode()
    if len(value) < 32:
        raise HTTPException(status_code=503, detail="watermark key is not configured safely")
    return value


def _image_bytes(image: Image.Image, format_name: str = "PNG") -> bytes:
    output = BytesIO()
    image.save(output, format=format_name)
    return bytes(output.getvalue())


def _completed_job(session: Session, user: User, kind: str, result_url: str) -> Job:
    now = datetime.now(UTC)
    job = Job(
        owner_id=user.id, kind=kind, state=JobState.COMPLETED, progress=100,
        stage="completed", cancellable=False, result_url=result_url,
        started_at=now, completed_at=now,
    )
    session.add(job)
    return job


@router.get("/health")
def health_alias() -> dict[str, str]:
    return {"status": "ready"}

@router.get("/profiles")
def profiles(user: User = Depends(get_current_user)) -> dict[str, object]:
    del user
    return _page([
        {"id": str(identifier), "name": name, "type": kind,
         "description": "Authenticated opaque payload; measured output quality."}
        for identifier, (name, kind, _) in PROFILE_IDS.items()
    ])


@router.post("/assets/{asset_id}/protect", dependencies=[Depends(require_csrf)])
def protect_asset(
    asset_id: UUID, payload: ProtectRequest, request: Request,
    user: User = Depends(get_current_user), session: Session = Depends(get_db),
) -> dict[str, object]:
    asset = get_owned(session, Asset, asset_id, user.id)
    if asset is None:
        raise HTTPException(status_code=404, detail="asset not found")
    profile = PROFILE_IDS.get(payload.profile_id)
    if profile is None:
        raise HTTPException(status_code=422, detail="unknown protection profile")
    original = Image.open(BytesIO(request.app.state.storage.get("originals", asset.original_object_key)))
    token = uuid4()
    kind = profile[1]
    watermark_payload = WatermarkPayload(
        payload_type=PayloadType.OWNERSHIP,
        algorithm_version=2 if kind == "robust" else 1,
        key_version=1,
        token=token.bytes,
    )
    engine = RobustWatermarkEngine(strength=profile[2]) if kind == "robust" else LSBWatermarkEngine()
    try:
        protected = engine.embed(original, watermark_payload, _key(request)).image
    except CapacityError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if payload.visible_text:
        protected = add_visible_text(
            protected, payload.visible_text,
            options=VisibleWatermarkOptions(opacity=96, position="bottom-right"),
        )
    encoded = _image_bytes(protected)
    object_key = new_object_key("png")
    request.app.state.storage.put("protected", object_key, encoded, "image/png")
    metrics = measure_quality(original, protected).as_dict()
    row = ProtectedOutput(
        owner_id=user.id, asset_id=asset.id, profile_id=None, token=token,
        algorithm_version=watermark_payload.algorithm_version, key_version=1,
        object_key=object_key, sha256=sha256(encoded).hexdigest(), metrics=metrics,
    )
    session.add(row)
    session.flush()
    job = _completed_job(session, user, "protect", f"/api/v1/outputs/{row.id}/download")
    session.commit()
    session.refresh(job)
    return _job_view(job)


@router.get("/outputs/{output_id}/download")
def download_output(
    output_id: UUID, request: Request, user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> Response:
    row = get_owned(session, ProtectedOutput, output_id, user.id)
    if row is None:
        raise HTTPException(status_code=404, detail="protected output not found")
    return Response(
        request.app.state.storage.get("protected", row.object_key),
        media_type="image/png",
        headers={"Content-Disposition": 'attachment; filename="tracemark-protected.png"',
                 "Cache-Control": "private, no-store"},
    )


def _job_view(job: Job) -> dict[str, object]:
    return {
        "id": str(job.id), "state": job.state.value, "stage": job.stage,
        "progress": job.progress, "cancellable": job.cancellable,
        "created_at": job.created_at.isoformat(), "updated_at": (job.completed_at or job.created_at).isoformat(),
        "result_url": job.result_url, "error": None,
    }


def _ensure_source_output(asset: Asset, request: Request, user: User, session: Session) -> ProtectedOutput:
    existing = session.scalar(
        select(ProtectedOutput).where(
            ProtectedOutput.asset_id == asset.id, ProtectedOutput.owner_id == user.id
        ).order_by(ProtectedOutput.created_at.desc())
    )
    if existing is not None:
        return existing
    original = Image.open(BytesIO(request.app.state.storage.get("originals", asset.original_object_key)))
    token = uuid4()
    payload = WatermarkPayload(PayloadType.OWNERSHIP, 2, 1, token.bytes)
    try:
        protected = RobustWatermarkEngine().embed(original, payload, _key(request)).image
    except CapacityError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    encoded = _image_bytes(protected)
    key = new_object_key("png")
    request.app.state.storage.put("protected", key, encoded, "image/png")
    row = ProtectedOutput(
        owner_id=user.id, asset_id=asset.id, token=token, algorithm_version=2,
        key_version=1, object_key=key, sha256=sha256(encoded).hexdigest(),
        metrics=measure_quality(original, protected).as_dict(),
    )
    session.add(row)
    session.flush()
    return row


@router.post("/distributions", dependencies=[Depends(require_csrf)])
def create_distribution(
    payload: DistributionRequest, request: Request,
    user: User = Depends(get_current_user), session: Session = Depends(get_db),
) -> dict[str, object]:
    asset = get_owned(session, Asset, payload.asset_id, user.id)
    if asset is None:
        raise HTTPException(status_code=404, detail="asset not found")
    source = _ensure_source_output(asset, request, user, session)
    original = Image.open(BytesIO(request.app.state.storage.get("originals", asset.original_object_key)))
    token = uuid4()
    wm = WatermarkPayload(PayloadType.DISTRIBUTION, 2, 1, token.bytes)
    try:
        marked = RobustWatermarkEngine(strength=36).embed(original, wm, _key(request)).image
    except CapacityError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    encoded = _image_bytes(marked)
    key = new_object_key("png")
    request.app.state.storage.put("protected", key, encoded, "image/png")
    row = DistributionCopy(
        owner_id=user.id, protected_output_id=source.id, token=token,
        recipient_label=payload.recipient_label, reference=payload.reference, object_key=key,
    )
    session.add(row)
    session.flush()
    job = _completed_job(session, user, "distribution", f"/api/v1/distributions/{row.id}/download")
    session.commit()
    session.refresh(job)
    return _job_view(job)


@router.get("/distributions")
def list_distributions(
    user: User = Depends(get_current_user), session: Session = Depends(get_db),
) -> dict[str, object]:
    rows = list(session.scalars(select(DistributionCopy).where(
        DistributionCopy.owner_id == user.id
    ).order_by(DistributionCopy.created_at.desc())))
    return _page([{
        "id": str(row.id), "asset_id": str(row.protected_output_id),
        "recipient_label": row.recipient_label or "Unlabelled copy",
        "reference": row.reference, "created_at": row.created_at.isoformat(),
        "download_url": f"/api/v1/distributions/{row.id}/download",
    } for row in rows])


@router.get("/distributions/{copy_id}/download")
def download_distribution(
    copy_id: UUID, request: Request, user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> Response:
    row = get_owned(session, DistributionCopy, copy_id, user.id)
    if row is None:
        raise HTTPException(status_code=404, detail="distribution not found")
    row.download_count += 1
    row.last_downloaded_at = datetime.now(UTC)
    session.commit()
    return Response(
        request.app.state.storage.get("protected", row.object_key),
        media_type="image/png",
        headers={"Content-Disposition": 'attachment; filename="tracemark-distribution.png"',
                 "Cache-Control": "private, no-store"},
    )


@router.post("/verification")
async def verify_image(
    request: Request, file: UploadFile = File(...),
    user: User = Depends(get_current_user), session: Session = Depends(get_db),
) -> dict[str, object]:
    data = await file.read(request.app.state.settings.max_upload_bytes + 1)
    await file.close()
    try:
        validated = validate_image(
            data, file.filename, file.content_type,
            max_bytes=request.app.state.settings.max_upload_bytes,
            max_pixels=request.app.state.settings.max_image_pixels,
        )
    except UploadRejected as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    image = Image.open(BytesIO(validated.content))
    exact_asset = session.scalar(select(Asset).where(
        Asset.owner_id == user.id, Asset.sha256 == validated.sha256
    ))
    extraction = RobustWatermarkEngine().extract(image, _key(request), key_versions=[1])
    classification = EvidenceClassification.NO_EVIDENCE
    matched_distribution = None
    matched_output = None
    if exact_asset is not None:
        classification = EvidenceClassification.EXACT_REGISTERED_HASH
    elif extraction.valid and extraction.payload is not None:
        token = UUID(bytes=extraction.payload.token)
        if extraction.payload.payload_type == PayloadType.DISTRIBUTION:
            matched_distribution = session.scalar(select(DistributionCopy).where(
                DistributionCopy.owner_id == user.id, DistributionCopy.token == token
            ))
            if matched_distribution is not None:
                classification = EvidenceClassification.VALID_DISTRIBUTION_WATERMARK
        else:
            matched_output = session.scalar(select(ProtectedOutput).where(
                ProtectedOutput.owner_id == user.id, ProtectedOutput.token == token
            ))
            if matched_output is not None:
                classification = EvidenceClassification.VALID_OWNERSHIP_WATERMARK
    if classification == EvidenceClassification.NO_EVIDENCE and extraction.integrity_error == "PayloadIntegrityError":
        classification = EvidenceClassification.INVALID_AUTHENTICATED_PAYLOAD
    query_fp = fingerprint(image)
    nearest = None
    nearest_distance = None
    for asset in session.scalars(select(Asset).where(Asset.owner_id == user.id)):
        value = asset.fingerprints.get("phash") if asset.fingerprints else None
        if value is None:
            continue
        distance = hamming_distance(query_fp.phash, int(value, 16))
        if nearest_distance is None or distance < nearest_distance:
            nearest, nearest_distance = asset, distance
    if classification == EvidenceClassification.NO_EVIDENCE and nearest_distance is not None:
        if nearest_distance <= 6:
            classification = EvidenceClassification.CALIBRATED_VISUAL_DERIVATIVE
        elif nearest_distance <= 12:
            classification = EvidenceClassification.POSSIBLE_VISUAL_MATCH
    with TemporaryDirectory(prefix="tracemark-provenance-") as temporary_directory:
        provenance_input = Path(temporary_directory) / f"submitted.{validated.extension}"
        provenance_input.write_bytes(validated.content)
        provenance = C2PAProvenanceAdapter().verify(provenance_input)
    provenance_state = (
        ProvenanceState.NOT_PRESENT
        if provenance.state.value == "absent"
        else ProvenanceState(provenance.state.value)
    )
    evidence = {
        "exact_hash_match": exact_asset is not None,
        "watermark": {
            "valid": extraction.valid,
            "type": extraction.payload.payload_type.name.lower() if extraction.payload else None,
            "repetitions_found": extraction.repetitions_found,
            "corrected_symbols": extraction.corrected_symbols,
            "integrity_error": extraction.integrity_error,
        },
        "visual": {"phash_distance": nearest_distance, "matched_asset_id": str(nearest.id) if nearest else None},
        "provenance": {"state": provenance.state.value, "detail": provenance.detail},
        "matched_distribution_id": str(matched_distribution.id) if matched_distribution else None,
        "matched_output_id": str(matched_output.id) if matched_output else None,
    }
    row = VerificationEvidence(
        owner_id=user.id, classification=classification,
        integrity_state=IntegrityState.VALID if extraction.valid else IntegrityState.NOT_PRESENT,
        provenance_state=provenance_state,
        evidence=evidence, submitted_sha256=validated.sha256,
    )
    session.add(row)
    session.flush()
    snapshot = {"id": str(row.id), "classification": classification.value, **evidence}
    report_key = request.app.state.settings.report_key.encode()
    signature = hmac.new(report_key, json.dumps(snapshot, sort_keys=True).encode(), "sha256").hexdigest()
    report = Report(
        owner_id=user.id, kind="verification", evidence_snapshot=snapshot,
        evidence_hmac=signature, object_keys={},
    )
    session.add(report)
    session.commit()
    return {"id": str(row.id), "classification": classification.value,
            "created_at": row.created_at.isoformat(), **evidence}


@router.get("/collections")
def collections(
    user: User = Depends(get_current_user), session: Session = Depends(get_db),
) -> dict[str, object]:
    rows = list(session.scalars(select(Collection).where(Collection.owner_id == user.id)))
    items = []
    for row in rows:
        item_count = session.scalar(
            select(func.count()).select_from(IndexedMedia).where(
                IndexedMedia.owner_id == user.id, IndexedMedia.collection_id == row.id
            )
        ) or 0
        items.append({"id": str(row.id), "name": row.name, "item_count": item_count,
                      "updated_at": row.updated_at.isoformat(), "state": "completed"})
    return _page(items)


@router.post("/collections", dependencies=[Depends(require_csrf)])
def create_collection(
    payload: CollectionRequest, user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> dict[str, object]:
    row = Collection(owner_id=user.id, name=payload.name.strip())
    session.add(row)
    session.commit()
    session.refresh(row)
    return {"id": str(row.id), "name": row.name, "item_count": 0,
            "updated_at": row.updated_at.isoformat(), "state": "completed"}


@router.post("/collections/{collection_id}/items", dependencies=[Depends(require_csrf)])
async def add_collection_item(
    collection_id: UUID, request: Request, file: UploadFile = File(...),
    user: User = Depends(get_current_user), session: Session = Depends(get_db),
) -> dict[str, object]:
    collection = get_owned(session, Collection, collection_id, user.id)
    if collection is None:
        raise HTTPException(status_code=404, detail="collection not found")
    data = await file.read(request.app.state.settings.max_upload_bytes + 1)
    await file.close()
    try:
        validated = validate_image(
            data, file.filename, file.content_type,
            max_bytes=request.app.state.settings.max_upload_bytes,
            max_pixels=request.app.state.settings.max_image_pixels,
        )
    except UploadRejected as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    existing = session.scalar(select(IndexedMedia).where(
        IndexedMedia.collection_id == collection.id, IndexedMedia.sha256 == validated.sha256
    ))
    if existing is not None:
        return {"id": str(existing.id), "duplicate": True}
    image = Image.open(BytesIO(validated.content))
    fp = fingerprint(image)
    key = new_object_key(validated.extension)
    request.app.state.storage.put("originals", key, validated.content, validated.mime_type)
    row = IndexedMedia(
        owner_id=user.id, collection_id=collection.id, object_key=key,
        sha256=validated.sha256,
        fingerprints={"phash": f"{fp.phash:016x}", "dhash": f"{fp.dhash:016x}", "whash": f"{fp.whash:016x}"},
        source_label=validated.display_name,
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return {"id": str(row.id), "duplicate": False}


@router.get("/collections/{collection_id}/items")
def collection_items(
    collection_id: UUID,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> dict[str, object]:
    collection = get_owned(session, Collection, collection_id, user.id)
    if collection is None:
        raise HTTPException(status_code=404, detail="collection not found")
    rows = session.scalars(
        select(IndexedMedia).where(
            IndexedMedia.owner_id == user.id, IndexedMedia.collection_id == collection.id
        ).order_by(IndexedMedia.created_at.desc())
    )
    return _page([
        {"id": str(row.id), "source": row.source_label, "sha256": row.sha256,
         "created_at": row.created_at.isoformat()} for row in rows
    ])


@router.post("/collections/{collection_id}/zip", dependencies=[Depends(require_csrf)])
async def add_collection_zip(
    collection_id: UUID,
    request: Request,
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> dict[str, object]:
    collection = get_owned(session, Collection, collection_id, user.id)
    if collection is None:
        raise HTTPException(status_code=404, detail="collection not found")
    archive_limit = min(request.app.state.settings.max_upload_bytes * 4, 100 * 1024 * 1024)
    content = await file.read(archive_limit + 1)
    await file.close()
    try:
        entries = validated_zip_images(content, max_archive_bytes=archive_limit)
        validated_entries = [
            validate_image(
                entry, name, None,
                max_bytes=request.app.state.settings.max_upload_bytes,
                max_pixels=request.app.state.settings.max_image_pixels,
            )
            for name, entry in entries
        ]
    except UploadRejected as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    created_keys: list[str] = []
    added = 0
    duplicates = 0
    try:
        for validated in validated_entries:
            existing = session.scalar(select(IndexedMedia).where(
                IndexedMedia.owner_id == user.id,
                IndexedMedia.collection_id == collection.id,
                IndexedMedia.sha256 == validated.sha256,
            ))
            if existing is not None:
                duplicates += 1
                continue
            image = Image.open(BytesIO(validated.content))
            media_fingerprint = fingerprint(image)
            key = new_object_key(validated.extension)
            request.app.state.storage.put("originals", key, validated.content, validated.mime_type)
            created_keys.append(key)
            session.add(IndexedMedia(
                owner_id=user.id,
                collection_id=collection.id,
                object_key=key,
                sha256=validated.sha256,
                fingerprints={
                    "phash": f"{media_fingerprint.phash:016x}",
                    "dhash": f"{media_fingerprint.dhash:016x}",
                    "whash": f"{media_fingerprint.whash:016x}",
                },
                source_label=validated.display_name,
            ))
            added += 1
        session.commit()
    except Exception:
        session.rollback()
        for key in created_keys:
            request.app.state.storage.delete("originals", key)
        raise
    return {"added": added, "duplicates": duplicates, "unsupported": 0}


@router.post("/collections/{collection_id}/rescan", dependencies=[Depends(require_csrf)])
def rescan_collection(
    collection_id: UUID,
    request: Request,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> dict[str, object]:
    collection = get_owned(session, Collection, collection_id, user.id)
    if collection is None:
        raise HTTPException(status_code=404, detail="collection not found")
    rows = list(session.scalars(select(IndexedMedia).where(
        IndexedMedia.owner_id == user.id, IndexedMedia.collection_id == collection.id
    )))
    for row in rows:
        image = Image.open(BytesIO(request.app.state.storage.get("originals", row.object_key)))
        media_fingerprint = fingerprint(image)
        row.fingerprints = {
            "phash": f"{media_fingerprint.phash:016x}",
            "dhash": f"{media_fingerprint.dhash:016x}",
            "whash": f"{media_fingerprint.whash:016x}",
        }
    session.commit()
    return {"rescanned": len(rows), "state": "completed"}


@router.delete("/collections/{collection_id}", dependencies=[Depends(require_csrf)])
def delete_collection(
    collection_id: UUID,
    request: Request,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> Response:
    collection = get_owned(session, Collection, collection_id, user.id)
    if collection is None:
        raise HTTPException(status_code=404, detail="collection not found")
    rows = list(session.scalars(select(IndexedMedia).where(
        IndexedMedia.owner_id == user.id, IndexedMedia.collection_id == collection.id
    )))
    for row in rows:
        request.app.state.storage.delete("originals", row.object_key)
        if row.thumbnail_object_key:
            request.app.state.storage.delete("thumbnails", row.thumbnail_object_key)
    session.delete(collection)
    session.commit()
    return Response(status_code=204)

@router.post("/collections/{collection_id}/search")
async def search_collection(
    collection_id: UUID, request: Request, file: UploadFile = File(...),
    user: User = Depends(get_current_user), session: Session = Depends(get_db),
) -> dict[str, object]:
    collection = get_owned(session, Collection, collection_id, user.id)
    if collection is None:
        raise HTTPException(status_code=404, detail="collection not found")
    data = await file.read(request.app.state.settings.max_upload_bytes + 1)
    await file.close()
    try:
        validated = validate_image(
            data, file.filename, file.content_type,
            max_bytes=request.app.state.settings.max_upload_bytes,
            max_pixels=request.app.state.settings.max_image_pixels,
        )
    except UploadRejected as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    query_fp = fingerprint(Image.open(BytesIO(validated.content)))
    results = []
    for row in session.scalars(select(IndexedMedia).where(
        IndexedMedia.owner_id == user.id, IndexedMedia.collection_id == collection.id
    )):
        distance = hamming_distance(query_fp.phash, int(row.fingerprints["phash"], 16))
        if row.sha256 == validated.sha256 or distance <= 16:
            results.append({"id": str(row.id), "source": row.source_label,
                            "exact": row.sha256 == validated.sha256,
                            "phash_distance": distance})
    results.sort(key=lambda item: (not item["exact"], item["phash_distance"]))
    return _page(results)


@router.get("/searches")
def searches(
    q: str, user: User = Depends(get_current_user), session: Session = Depends(get_db),
) -> dict[str, object]:
    term = q.strip()[:200]
    assets = list(session.scalars(select(Asset).where(
        Asset.owner_id == user.id,
        or_(Asset.display_name.ilike(f"%{term}%"), Asset.sha256.ilike(f"%{term}%")),
    ).limit(50)))
    return _page([{"id": str(row.id), "title": row.display_name,
                   "classification": "registered_asset",
                   "detail": f"{row.mime_type}; {row.width} x {row.height}",
                   "href": f"/app/assets/{row.id}"} for row in assets])


@router.get("/scans")
def scans(user: User = Depends(get_current_user), session: Session = Depends(get_db)) -> dict[str, object]:
    rows = list(session.scalars(select(ScanSource).where(ScanSource.owner_id == user.id)))
    return _page([{"id": str(row.id), "url": row.submitted_url, "state": row.status,
                   "candidate_count": row.candidate_count,
                   "match_count": int(row.evidence.get("match_count", 0)),
                   "created_at": row.created_at.isoformat()} for row in rows])


@router.post("/scans", dependencies=[Depends(require_csrf)])
def create_scan(
    payload: ScanRequest, request: Request, user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> dict[str, object]:
    if not request.app.state.settings.scanner_enabled:
        raise HTTPException(status_code=503, detail="controlled scanner is disabled")
    from ..safe_fetch import SafeFetcher
    fetcher = SafeFetcher(max_candidates=10)
    submitted = str(payload.url)
    first = fetcher.fetch(submitted)
    candidates = [first] if first.content_type.startswith("image/") else []
    candidate_urls: list[str] = []
    if first.content_type == "text/html":
        _, candidate_urls = fetcher.extract_page_images(submitted)
        for candidate_url in candidate_urls:
            try:
                candidates.append(fetcher.fetch_image(candidate_url))
            except HTTPException:
                continue
    matches: list[dict[str, object]] = []
    assets = list(session.scalars(select(Asset).where(Asset.owner_id == user.id)))
    for candidate in candidates:
        try:
            remote_image = Image.open(BytesIO(candidate.body))
            remote_fp = fingerprint(remote_image)
        except Exception as exc:
            logger.debug("Skipping unsupported scan candidate: %s", type(exc).__name__)
            continue
        for asset in assets:
            stored = asset.fingerprints.get("phash") if asset.fingerprints else None
            if stored is None:
                continue
            distance = hamming_distance(remote_fp.phash, int(stored, 16))
            if distance <= 12:
                matches.append({"url": candidate.final_url, "asset_id": str(asset.id), "phash_distance": distance})
    row = ScanSource(
        owner_id=user.id, submitted_url=submitted, final_url=first.final_url,
        status="completed", candidate_count=len(candidates),
        evidence={"match_count": len(matches), "matches": matches, "candidate_urls": candidate_urls},
    )
    session.add(row)
    session.flush()
    job = _completed_job(session, user, "scan", f"/api/v1/scans/{row.id}")
    session.commit()
    session.refresh(job)
    return _job_view(job)


@router.get("/benchmarks")
def benchmarks(
    user: User = Depends(get_current_user), session: Session = Depends(get_db),
) -> dict[str, object]:
    rows = list(session.scalars(select(BenchmarkRun).where(
        BenchmarkRun.owner_id == user.id
    ).order_by(BenchmarkRun.created_at.desc())))
    items = []
    for row in rows:
        results = list(session.scalars(select(BenchmarkResult).where(BenchmarkResult.run_id == row.id)))
        items.append({"id": str(row.id), "name": f"{row.profile.title()} benchmark",
                      "profile": row.profile, "state": row.state.value,
                      "created_at": row.created_at.isoformat(),
                      "results": [result.metrics for result in results]})
    return _page(items)


@router.post("/benchmarks", dependencies=[Depends(require_csrf)])
def create_benchmark(
    payload: BenchmarkRequest, request: Request,
    user: User = Depends(get_current_user), session: Session = Depends(get_db),
) -> dict[str, object]:
    output = session.scalar(select(ProtectedOutput).where(
        ProtectedOutput.owner_id == user.id
    ).order_by(ProtectedOutput.created_at.desc()))
    if output is None:
        raise HTTPException(status_code=409, detail="protect an asset before running a benchmark")
    asset = get_owned(session, Asset, output.asset_id, user.id)
    if asset is None:
        raise HTTPException(status_code=404, detail="benchmark asset not found")
    robust_source = Image.open(BytesIO(request.app.state.storage.get("protected", output.object_key)))
    original = Image.open(BytesIO(request.app.state.storage.get("originals", asset.original_object_key)))
    lsb_payload = WatermarkPayload(PayloadType.OWNERSHIP, 1, 1, secrets.token_bytes(16))
    lsb_source = LSBWatermarkEngine().embed(original, lsb_payload, _key(request)).image

    cases = [("clean", "none")]
    cases.append(("jpeg", "quality=85"))
    if payload.profile in {"standard", "aggressive"}:
        cases.extend([("jpeg", "quality=60"), ("resize", "scale=0.75")])
    if payload.profile == "aggressive":
        cases.extend([("jpeg", "quality=40"), ("resize", "scale=0.50")])

    def transform(image: Image.Image, transformation: str, parameter: str) -> Image.Image:
        if transformation == "clean":
            return image.copy()
        if transformation == "jpeg":
            quality = int(parameter.split("=")[1])
            stream = BytesIO()
            image.convert("RGB").save(stream, format="JPEG", quality=quality)
            return Image.open(BytesIO(stream.getvalue())).copy()
        scale = float(parameter.split("=")[1])
        return image.resize(
            (max(1, int(image.width * scale)), max(1, int(image.height * scale))),
            Image.Resampling.LANCZOS,
        )

    row = BenchmarkRun(
        owner_id=user.id, profile=payload.profile, seed=20260720,
        state=JobState.RUNNING, configuration={"profile": payload.profile, "cases": cases},
    )
    session.add(row)
    session.flush()
    for transformation, parameter in cases:
        robust_candidate = transform(robust_source, transformation, parameter)
        started = perf_counter()
        lsb_candidate = transform(lsb_source, transformation, parameter)
        robust_result = RobustWatermarkEngine().extract(robust_candidate, _key(request), key_versions=[1])
        lsb_result = LSBWatermarkEngine().extract(lsb_candidate, _key(request), key_versions=[1])
        metrics = {
            "transformation": transformation, "parameter": parameter,
            "robust_detected": robust_result.valid, "lsb_detected": lsb_result.valid,
            "robust_corrected_symbols": robust_result.corrected_symbols,
            "lsb_corrected_symbols": lsb_result.corrected_symbols,
        }
        if robust_candidate.size == robust_source.size:
            quality = measure_quality(robust_source, robust_candidate)
            metrics.update({"ssim": quality.ssim, "psnr": quality.psnr_db})
        session.add(BenchmarkResult(
            run_id=row.id, transformation=transformation,
            parameters={"parameter": parameter}, detected=robust_result.valid,
            metrics=metrics, duration_ms=(perf_counter() - started) * 1000.0,
        ))
    row.state = JobState.COMPLETED
    row.completed_at = datetime.now(UTC)
    job = _completed_job(session, user, "benchmark", f"/api/v1/benchmarks/{row.id}")
    session.commit()
    session.refresh(job)
    return _job_view(job)


@router.get("/reports")
def reports(user: User = Depends(get_current_user), session: Session = Depends(get_db)) -> dict[str, object]:
    rows = list(session.scalars(select(Report).where(Report.owner_id == user.id)))
    return _page([{"id": str(row.id), "kind": row.kind,
                   "title": f"{row.kind.title()} evidence {str(row.id)[:8]}",
                   "created_at": row.created_at.isoformat(), "formats": ["json", "html", "pdf"]}
                  for row in rows])


@router.get("/reports/{report_id}/download")
def report_download(
    report_id: UUID, format: str, user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> Response:
    row = get_owned(session, Report, report_id, user.id)
    if row is None:
        raise HTTPException(status_code=404, detail="report not found")
    payload = {**row.evidence_snapshot, "evidence_hmac": row.evidence_hmac,
               "generated_at": row.created_at.isoformat(),
               "limitations": "Forensic evidence is not conclusive legal proof or proof of intent."}
    if format == "json":
        return Response(json.dumps(payload, indent=2), media_type="application/json")
    if format == "html":
        escaped = json.dumps(payload, indent=2).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        html = f"<!doctype html><meta charset='utf-8'><title>TraceMark report</title><h1>TraceMark forensic evidence</h1><pre>{escaped}</pre>"
        return Response(html, media_type="text/html")
    if format == "pdf":
        from reportlab.lib.pagesizes import A4  # type: ignore[import-untyped]
        from reportlab.pdfgen import canvas  # type: ignore[import-untyped]
        stream = BytesIO()
        document = canvas.Canvas(stream, pagesize=A4)
        document.setTitle("TraceMark forensic evidence")
        document.drawString(48, 800, "TraceMark forensic evidence report")
        text = document.beginText(48, 775)
        text.setFont("Helvetica", 8)
        for line in json.dumps(payload, indent=2).splitlines():
            text.textLine(line[:110])
            if text.getY() < 48:
                document.drawText(text)
                document.showPage()
                text = document.beginText(48, 800)
                text.setFont("Helvetica", 8)
        document.drawText(text)
        document.save()
        return Response(stream.getvalue(), media_type="application/pdf")
    raise HTTPException(status_code=422, detail="supported report formats are json, html, and pdf")


@router.get("/settings")
def settings(request: Request, user: User = Depends(get_current_user)) -> dict[str, object]:
    del user
    provenance_state = (
        "adapter_available" if C2PAProvenanceAdapter._sdk() is not None else "unsupported"
    )
    return {"scanning_enabled": request.app.state.settings.scanner_enabled,
            "provenance_state": provenance_state, "active_key_version": 1,
            "supported_formats": ["JPEG", "PNG", "WebP"]}


@router.get("/system/dashboard")
def dashboard(user: User = Depends(get_current_user), session: Session = Depends(get_db)) -> dict[str, object]:
    jobs = list(session.scalars(select(Job).where(Job.owner_id == user.id).order_by(Job.created_at.desc()).limit(10)))
    return {
        "asset_count": session.scalar(select(func.count()).select_from(Asset).where(Asset.owner_id == user.id)) or 0,
        "protected_count": session.scalar(select(func.count()).select_from(ProtectedOutput).where(ProtectedOutput.owner_id == user.id)) or 0,
        "collection_count": session.scalar(select(func.count()).select_from(Collection).where(Collection.owner_id == user.id)) or 0,
        "active_job_count": sum(job.state in {JobState.QUEUED, JobState.RUNNING} for job in jobs),
        "recent_jobs": [_job_view(job) for job in jobs],
    }

