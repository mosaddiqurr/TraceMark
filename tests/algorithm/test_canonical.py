from __future__ import annotations

from io import BytesIO

import numpy as np
import pytest
from PIL import Image
from tracemark_watermark import (
    CanonicalWatermarkEngine,
    CapacityError,
    PayloadType,
    RobustWatermarkEngine,
    WatermarkPayload,
    measure_quality,
)

KEY = b"c" * 32


def _photo_like(width: int = 900, height: int = 640, *, alpha: bool = False) -> Image.Image:
    rng = np.random.default_rng(20261022)
    y, x = np.indices((height, width))
    values = np.empty((height, width, 4 if alpha else 3), dtype=np.uint8)
    noise = rng.integers(0, 24, size=(height, width))
    values[..., 0] = np.clip(120 + 60 * np.sin(x / 37) + 40 * np.cos(y / 23) + noise, 0, 255)
    values[..., 1] = np.clip(110 + 50 * np.cos(x / 29 + y / 41) + noise, 0, 255)
    values[..., 2] = np.clip(100 + 70 * np.sin((x + y) / 53) + noise // 2, 0, 255)
    if alpha:
        values[..., 3] = ((x + y) % 192 + 63).astype(np.uint8)
    return Image.fromarray(values, "RGBA" if alpha else "RGB")


def _jpeg(image: Image.Image, quality: int) -> Image.Image:
    stream = BytesIO()
    image.convert("RGB").save(stream, format="JPEG", quality=quality)
    stream.seek(0)
    return Image.open(stream).copy()


def _payload(token: bytes = b"V" * 16) -> WatermarkPayload:
    return WatermarkPayload(PayloadType.DISTRIBUTION, 3, 1, token)


def test_canonical_round_trip_preserves_alpha_and_quality() -> None:
    source = _photo_like(alpha=True)
    engine = CanonicalWatermarkEngine()

    embedded = engine.embed(source, _payload(), KEY)
    extracted = engine.extract(embedded.image, KEY, key_versions=[1])

    assert extracted.valid is True
    assert extracted.payload == _payload()
    assert extracted.repetitions_found >= 1
    assert embedded.image.size == source.size
    assert embedded.image.getchannel("A").tobytes() == source.getchannel("A").tobytes()
    assert measure_quality(source, embedded.image).psnr_db >= 38.0


@pytest.mark.parametrize(
    "transform",
    [
        pytest.param(lambda image: image.resize((675, 480), Image.Resampling.LANCZOS), id="resize-75"),
        pytest.param(
            lambda image: _jpeg(image.resize((450, 320), Image.Resampling.LANCZOS), 80), id="resize-50-jpeg-80"
        ),
        pytest.param(lambda image: image.resize((1350, 960), Image.Resampling.BICUBIC), id="upscale-150"),
        pytest.param(lambda image: image.resize((900, 500), Image.Resampling.BILINEAR), id="aspect-change"),
        pytest.param(lambda image: _jpeg(image, 70), id="jpeg-70"),
    ],
)
def test_canonical_survives_resizing_and_compression(transform) -> None:  # type: ignore[no-untyped-def]
    engine = CanonicalWatermarkEngine()
    embedded = engine.embed(_photo_like(), _payload(), KEY).image

    extracted = engine.extract(transform(embedded), KEY, key_versions=[1])

    assert extracted.valid is True
    assert extracted.payload == _payload()


def test_canonical_rejects_wrong_key_and_unmarked_images() -> None:
    source = _photo_like()
    engine = CanonicalWatermarkEngine()
    embedded = engine.embed(source, _payload(), KEY).image

    assert engine.extract(embedded, b"d" * 32, key_versions=[1]).valid is False
    assert engine.extract(source, KEY, key_versions=[1]).valid is False


def test_canonical_and_v2_marks_do_not_cross_decode() -> None:
    source = _photo_like()
    canonical = CanonicalWatermarkEngine().embed(source, _payload(), KEY).image
    legacy = RobustWatermarkEngine().embed(source, WatermarkPayload(PayloadType.OWNERSHIP, 2, 1, b"L" * 16), KEY).image

    assert RobustWatermarkEngine().extract(canonical, KEY, key_versions=[1]).valid is False
    assert CanonicalWatermarkEngine().extract(legacy, KEY, key_versions=[1]).valid is False


def test_canonical_requires_minimum_dimension() -> None:
    small = Image.new("RGB", (300, 200), "gray")
    engine = CanonicalWatermarkEngine()

    assert engine.capacity(small).fits is False
    with pytest.raises(CapacityError):
        engine.embed(small, _payload(), KEY)
    assert engine.extract(Image.new("RGB", (32, 32)), KEY, key_versions=[1]).integrity_error == "insufficient_capacity"


def test_canonical_rejects_payload_for_other_algorithm() -> None:
    with pytest.raises(ValueError, match="canonical v3"):
        CanonicalWatermarkEngine().embed(_photo_like(), WatermarkPayload(PayloadType.OWNERSHIP, 2, 1, b"W" * 16), KEY)
