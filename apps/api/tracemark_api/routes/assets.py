from __future__ import annotations

from io import BytesIO
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile, status
from fastapi.responses import Response
from PIL import Image
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from tracemark_watermark import fingerprint

from ..database import get_db
from ..dependencies import get_current_user, require_csrf
from ..logging_config import correlation_id_var
from ..models import Asset, AuditEvent, ProtectedOutput, User
from ..schemas import AssetDetail, AssetList, AssetView, ProtectedOutputSummary
from ..scoping import get_owned
from ..storage import new_object_key
from ..uploads import UploadRejected, validate_image

router = APIRouter(prefix="/assets", tags=["assets"])


@router.post(
    "",
    response_model=AssetView,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_csrf)],
)
async def create_asset(
    request: Request,
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> Asset:
    maximum = request.app.state.settings.max_upload_bytes
    content = await file.read(maximum + 1)
    await file.close()
    try:
        image = validate_image(
            content,
            file.filename,
            file.content_type,
            max_bytes=maximum,
            max_pixels=request.app.state.settings.max_image_pixels,
        )
    except UploadRejected as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    decoded = Image.open(BytesIO(image.content))
    fp = fingerprint(decoded)
    key = new_object_key(image.extension)
    request.app.state.storage.put("originals", key, image.content, image.mime_type)
    asset = Asset(
        owner_id=user.id,
        display_name=image.display_name,
        original_object_key=key,
        sha256=image.sha256,
        mime_type=image.mime_type,
        width=image.width,
        height=image.height,
        byte_size=len(image.content),
        safe_metadata={"format": image.extension.upper()},
        fingerprints={"phash": f"{fp.phash:016x}", "dhash": f"{fp.dhash:016x}", "whash": f"{fp.whash:016x}", "pixel_sha256": fp.pixel_sha256},
    )
    session.add(asset)
    session.add(
        AuditEvent(
            actor_user_id=user.id,
            action="asset.created",
            resource_type="asset",
            resource_id=asset.id,
            correlation_id=correlation_id_var.get(),
            details={"mime_type": image.mime_type, "byte_size": len(image.content)},
        )
    )
    try:
        session.commit()
    except Exception:
        request.app.state.storage.delete("originals", key)
        raise
    session.refresh(asset)
    return asset


@router.get("", response_model=AssetList)
def list_assets(
    page: int = Query(1, ge=1, le=100000),
    page_size: int = Query(25, ge=1, le=100),
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> AssetList:
    total = session.scalar(select(func.count()).select_from(Asset).where(Asset.owner_id == user.id)) or 0
    items = list(
        session.scalars(
            select(Asset)
            .where(Asset.owner_id == user.id)
            .order_by(Asset.created_at.desc(), Asset.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    )
    return AssetList(items=[AssetView.model_validate(item) for item in items], page=page, page_size=page_size, total=total)


@router.get("/{asset_id}", response_model=AssetDetail)
def get_asset(
    asset_id: UUID, user: User = Depends(get_current_user), session: Session = Depends(get_db)
) -> AssetDetail:
    asset = get_owned(session, Asset, asset_id, user.id)
    if asset is None:
        raise HTTPException(status_code=404, detail="asset not found")
    outputs = session.scalars(
        select(ProtectedOutput).where(
            ProtectedOutput.owner_id == user.id, ProtectedOutput.asset_id == asset.id
        ).order_by(ProtectedOutput.created_at.desc())
    )
    return AssetDetail(
        **AssetView.model_validate(asset).model_dump(),
        protected_outputs=[
            ProtectedOutputSummary(
                id=output.id,
                type="lsb" if output.algorithm_version == 1 else "robust",
                created_at=output.created_at,
                download_url=f"/api/v1/protected-outputs/{output.id}/download",
                metrics=output.metrics,
            )
            for output in outputs
        ],
    )


@router.get("/{asset_id}/download")
def download_asset(
    asset_id: UUID,
    request: Request,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> Response:
    asset = get_owned(session, Asset, asset_id, user.id)
    if asset is None:
        raise HTTPException(status_code=404, detail="asset not found")
    content = request.app.state.storage.get("originals", asset.original_object_key)
    headers = {"Content-Disposition": f'attachment; filename="{asset.display_name}"', "Cache-Control": "private, no-store"}
    return Response(content, media_type=asset.mime_type, headers=headers)

