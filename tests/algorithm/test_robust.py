from __future__ import annotations

from io import BytesIO

import numpy as np
import pytest
from PIL import Image
from tracemark_watermark import (
    CapacityError,
    PayloadType,
    RobustWatermarkEngine,
    WatermarkPayload,
    measure_quality,
)


def _textured_image(size: int = 512, *, alpha: bool = False) -> Image.Image:
    rng = np.random.default_rng(20260720)
    y, x = np.indices((size, size))
    values = np.empty((size, size, 4 if alpha else 3), dtype=np.uint8)
    noise = rng.integers(0, 32, size=(size, size), dtype=np.uint8)
    values[..., 0] = (x // 2 + y // 3 + noise) % 256
    values[..., 1] = (x // 5 + y // 2 + noise // 2) % 256
    values[..., 2] = (x // 3 + y // 7 + noise) % 256
    if alpha:
        values[..., 3] = ((x + y) % 192 + 63).astype(np.uint8)
    return Image.fromarray(values, "RGBA" if alpha else "RGB")


def test_robust_clean_blind_round_trip_and_quality() -> None:
    source = _textured_image(alpha=True)
    engine = RobustWatermarkEngine()
    payload = WatermarkPayload(PayloadType.DISTRIBUTION, 2, 9, b"R" * 16)

    embedded = engine.embed(source, payload, b"z" * 32)
    extracted = engine.extract(embedded.image, b"z" * 32, key_versions=[8, 9])
    quality = measure_quality(source, embedded.image)

    assert extracted.valid is True
    assert extracted.payload == payload
    assert extracted.repetitions_found >= 1
    assert extracted.corrected_symbols is not None
    assert quality.ssim >= 0.95
    assert embedded.image.getchannel("A").tobytes() == source.getchannel("A").tobytes()
    assert len(extracted.bit_reliabilities) == 58 * 8


def test_robust_survives_high_quality_jpeg() -> None:
    source = _textured_image()
    engine = RobustWatermarkEngine(strength=36.0)
    payload = WatermarkPayload(PayloadType.OWNERSHIP, 2, 2, b"J" * 16)
    embedded = engine.embed(source, payload, b"w" * 32)
    stream = BytesIO()
    embedded.image.save(stream, format="JPEG", quality=95, subsampling=0)
    stream.seek(0)
    recompressed = Image.open(stream).copy()

    extracted = engine.extract(recompressed, b"w" * 32, key_versions=[2])

    assert extracted.valid is True
    assert extracted.payload == payload


def test_robust_wrong_key_is_not_accepted() -> None:
    source = _textured_image()
    payload = WatermarkPayload(PayloadType.OWNERSHIP, 2, 1, b"X" * 16)
    embedded = RobustWatermarkEngine().embed(source, payload, b"a" * 32)

    extracted = RobustWatermarkEngine().extract(embedded.image, b"b" * 32, key_versions=[1])

    assert extracted.valid is False
    assert extracted.payload is None


def test_robust_refuses_small_image_instead_of_reducing_redundancy() -> None:
    source = Image.new("RGB", (256, 256), "gray")
    payload = WatermarkPayload(PayloadType.OWNERSHIP, 2, 1, b"S" * 16)
    engine = RobustWatermarkEngine(repetitions=3)

    assert engine.capacity(source).fits is False
    with pytest.raises(CapacityError):
        engine.embed(source, payload, b"k" * 32)
