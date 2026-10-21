"""Real engine operations in memory, invoked only inside timed child processes."""

from __future__ import annotations

import math
from dataclasses import asdict
from hashlib import sha256
from io import BytesIO
from pathlib import Path
from typing import Any
from uuid import UUID

from PIL import Image, ImageOps
from tracemark_watermark import (
    C2PAProvenanceAdapter,
    CanonicalWatermarkEngine,
    ClassicalSimilarityEngine,
    LSBWatermarkEngine,
    PayloadType,
    RobustWatermarkEngine,
    WatermarkPayload,
    fingerprint,
    hamming_distance,
    measure_quality,
)

from .settings import Settings
from .uploads import UploadRejected, validate_image


def _decoded(data: bytes, filename: str, mime: str, settings: Settings) -> tuple[Image.Image, dict[str, Any]]:
    validated = validate_image(
        data,
        filename,
        mime,
        max_bytes=settings.max_upload_bytes,
        max_pixels=settings.max_image_pixels,
        max_dimension=settings.max_image_dimension,
    )
    with Image.open(BytesIO(data)) as source:
        image = source.copy()
    return image, {
        "filename": validated.display_name,
        "media_type": validated.mime_type,
        "width": image.width,
        "height": image.height,
        "size_bytes": len(data),
        "sha256": validated.sha256,
    }


def protect(
    data: bytes, filename: str, mime: str, settings: Settings, identifier: str, labelled: bool
) -> dict[str, Any]:
    decoded, metadata = _decoded(data, filename, mime, settings)
    # Rotate protection inputs to their displayed EXIF orientation, then strip metadata.
    image = ImageOps.exif_transpose(decoded).convert("RGBA" if "A" in decoded.getbands() else "RGB")
    metadata.update({"width": image.width, "height": image.height})
    # Resolution-independent v3 survives resizing; v2 remains for images below its canonical size.
    engine: CanonicalWatermarkEngine | RobustWatermarkEngine = CanonicalWatermarkEngine()
    if not engine.capacity(image).fits:
        engine = RobustWatermarkEngine(strength=32.0)
    payload = WatermarkPayload(
        PayloadType.DISTRIBUTION if labelled else PayloadType.OWNERSHIP,
        engine.algorithm_version,
        1,
        UUID(identifier).bytes,
    )
    embedded = engine.embed(image, payload, settings.master_key.encode()).image
    embedded.info.clear()
    output = BytesIO()
    embedded.save(output, format="PNG")
    content = output.getvalue()
    if len(content) > settings.max_upload_bytes:
        raise UploadRejected("The protected PNG exceeds the upload limit. Choose a smaller image.")
    # Verify the encoded file, not only the pre-encoding pixels, before promising protection.
    with Image.open(BytesIO(content)) as encoded:
        recovered = engine.extract(encoded, settings.master_key.encode(), key_versions=[1])
    if not recovered.valid or recovered.payload != payload:
        raise UploadRejected("A reliable watermark could not be embedded in this image. Try a more detailed image.")
    quality = {
        k: v if not isinstance(v, float) or math.isfinite(v) else None
        for k, v in measure_quality(image, embedded).as_dict().items()
    }
    return {
        "content": content,
        "file": metadata,
        "output_sha256": sha256(content).hexdigest(),
        "descriptor": ClassicalSimilarityEngine.describe(image),
        "quality": quality,
        "payload_type": payload.payload_type.name.lower(),
        "profile": (
            "Resize-tolerant invisible · canonical DWT-DCT-QIM v3"
            if engine.algorithm_version == 3
            else "Balanced invisible · DWT-DCT-QIM v2"
        ),
    }


def verify(
    data: bytes,
    filename: str,
    mime: str,
    settings: Settings,
    references: list[dict[str, Any]],
    temporary: str | None = None,
) -> dict[str, Any]:
    image, metadata = _decoded(data, filename, mime, settings)
    candidates = [CanonicalWatermarkEngine().extract(image, settings.master_key.encode(), key_versions=[1])]
    extraction = candidates[0] if candidates[0].valid else None
    for strength in () if extraction else (32.0, 36.0, 42.0):
        candidate = RobustWatermarkEngine(strength=strength).extract(
            image, settings.master_key.encode(), key_versions=[1]
        )
        candidates.append(candidate)
        if candidate.valid:
            extraction = candidate
            break
    if extraction is None:
        baseline = LSBWatermarkEngine().extract(image, settings.master_key.encode(), key_versions=[1])
        candidates.append(baseline)
        extraction = next(
            (v for v in candidates if v.valid),
            next((v for v in candidates if v.integrity_error == "payload_hmac_invalid"), candidates[0]),
        )
    payload = extraction.payload if extraction.valid else None
    token = str(UUID(bytes=payload.token)) if payload else None
    matched = (
        next(
            (r for r in references if r["id"] == token and r["payload_type"] == payload.payload_type.name.lower()), None
        )
        if payload
        else None
    )
    exact = next((r for r in references if metadata["sha256"] in {r["source_sha256"], r["output_sha256"]}), None)
    query = fingerprint(image)
    nearest = min(
        references, key=lambda r: hamming_distance(query.phash, r["descriptor"]["fingerprint"]["phash"]), default=None
    )
    visual_reference = matched or exact or nearest
    visual = None
    if visual_reference is not None:
        visual = asdict(ClassicalSimilarityEngine().compare_descriptor(visual_reference["descriptor"], image))
    classification = "no_evidence"
    if matched:
        classification = (
            "valid_distribution_watermark"
            if payload and payload.payload_type == PayloadType.DISTRIBUTION
            else "valid_ownership_watermark"
        )
    elif payload:
        classification = "authenticated_unresolved"
    elif any(v.integrity_error == "payload_hmac_invalid" for v in candidates):
        classification = "invalid_authenticated_payload"
    elif exact:
        classification = "exact_registered_hash"
    elif visual and visual["phash_distance"] <= 12:
        classification = "possible_visual_match"
    if visual is not None:
        visual["reference_available"] = True
        visual["similar"] = visual["phash_distance"] <= 12
        visual["note"] = (
            "Visual similarity is supporting evidence, not watermark authentication. Thresholds are heuristic."
        )
    try:
        if temporary is None:
            raise OSError("temporary storage unavailable")
        path = Path(temporary) / "submitted-image"
        path.write_bytes(data)
        provenance = C2PAProvenanceAdapter().verify(path)
        provenance_view = {"state": provenance.state.value, "detail": provenance.detail}
    except OSError:
        provenance_view = {
            "state": "verification_unavailable",
            "detail": "Temporary provenance inspection was unavailable.",
        }
    return {
        "verified": matched is not None,
        "classification": classification,
        "identifier": matched["id"] if matched else None,
        "reference_label": matched["reference_label"] if matched else None,
        "source_filename": matched["source_name"] if matched else None,
        "protected_at": matched["protected_at"] if matched else None,
        "file": metadata,
        "watermark": {
            "authentic": payload is not None,
            "integrity_state": "valid"
            if payload
            else ("invalid" if classification == "invalid_authenticated_payload" else "not_recovered"),
            "type": payload.payload_type.name.lower() if payload else None,
            "algorithm_version": payload.algorithm_version if payload else None,
            "key_version": payload.key_version if payload else None,
            "algorithm": extraction.algorithm,
            "repetitions_found": extraction.repetitions_found,
            "corrected_symbols": extraction.corrected_symbols,
            "integrity_error": extraction.integrity_error,
        },
        "exact_hash": {
            "matched": exact is not None,
            "kind": (
                "protected_copy"
                if exact and metadata["sha256"] == exact["output_sha256"]
                else "source"
                if exact
                else None
            ),
        },
        "visual": visual,
        "provenance": provenance_view,
        "limitations": [
            "A recovered identifier links to a protected copy; it does not prove legal ownership or who shared it.",
            "Cropping, repainting, heavy recompression or deliberate removal can prevent recovery. Resizing is tolerated only within tested bounds; no transformation survival is guaranteed.",
            "Private trace mappings belong to this browser workspace and expire with its retention period.",
            "No aggregate confidence score or population false-positive rate is claimed.",
        ],
    }
