from __future__ import annotations

import math

import numpy as np
from PIL import Image
from tracemark_watermark import (
    C2PAProvenanceAdapter,
    ClassicalSimilarityEngine,
    ProvenanceState,
    VisibleWatermarkOptions,
    add_visible_logo,
    add_visible_text,
    difference_image,
    fingerprint,
    measure_quality,
)


def _image() -> Image.Image:
    y, x = np.indices((128, 128))
    data = np.stack(((x * 2) % 256, (y * 2) % 256, (x + y) % 256), axis=2)
    return Image.fromarray(data.astype(np.uint8), "RGB")


def test_identical_quality_and_fingerprints_are_exact() -> None:
    image = _image()
    metrics = measure_quality(image, image.copy())
    evidence = ClassicalSimilarityEngine().compare(image, image.copy())

    assert math.isinf(metrics.psnr_db)
    assert metrics.ssim == 1.0
    assert metrics.changed_pixels == 0
    assert difference_image(image, image).getbbox() is None
    assert evidence.exact_pixel_match is True
    assert evidence.phash_distance == 0
    assert evidence.dhash_distance == 0
    assert evidence.whash_distance == 0
    assert fingerprint(image) == fingerprint(image.copy())


def test_visual_watermarks_change_rgb_and_preserve_source_alpha() -> None:
    source = _image().convert("RGBA")
    alpha = Image.fromarray(np.tile(np.arange(128, dtype=np.uint8), (128, 1)), "L")
    source.putalpha(alpha)
    options = VisibleWatermarkOptions(opacity=180, position="center", scale=0.3)

    text_result = add_visible_text(source, "TraceMark", options=options)
    logo = Image.new("RGBA", (30, 20), (255, 0, 0, 255))
    logo_result = add_visible_logo(source, logo, options=options)

    assert text_result.getchannel("A").tobytes() == source.getchannel("A").tobytes()
    assert logo_result.getchannel("A").tobytes() == source.getchannel("A").tobytes()
    assert text_result.convert("RGB").tobytes() != source.convert("RGB").tobytes()
    assert logo_result.convert("RGB").tobytes() != source.convert("RGB").tobytes()


def test_optional_provenance_adapter_reports_absent_sdk_honestly(tmp_path) -> None:
    adapter = C2PAProvenanceAdapter()
    result = adapter.verify(tmp_path / "missing.jpg")

    assert result.state in {
        ProvenanceState.UNSUPPORTED,
        ProvenanceState.VERIFICATION_UNAVAILABLE,
    }
    assert result.detail

