from __future__ import annotations

import numpy as np
import pytest
from PIL import Image
from tracemark_watermark import (
    CapacityError,
    LSBWatermarkEngine,
    PayloadType,
    WatermarkPayload,
    measure_quality,
)


def _rgba_image(width: int = 80, height: int = 64) -> Image.Image:
    y, x = np.indices((height, width))
    values = np.empty((height, width, 4), dtype=np.uint8)
    values[..., 0] = (x * 3 + y) % 256
    values[..., 1] = (x + y * 5) % 256
    values[..., 2] = (x * 7 + y * 2) % 256
    values[..., 3] = (x * 2 + 64) % 256
    return Image.fromarray(values, "RGBA")


def test_lsb_clean_blind_round_trip_preserves_alpha() -> None:
    source = _rgba_image()
    key = b"k" * 32
    payload = WatermarkPayload(PayloadType.OWNERSHIP, 1, 4, b"A" * 16)
    engine = LSBWatermarkEngine()

    embedded = engine.embed(source, payload, key)
    extracted = engine.extract(embedded.image, key, key_versions=[2, 4])

    assert extracted.valid is True
    assert extracted.payload == payload
    assert extracted.corrected_symbols == 0
    assert embedded.image.getchannel("A").tobytes() == source.getchannel("A").tobytes()
    assert embedded.diagnostics["fragile"] is True
    assert measure_quality(source, embedded.image).maximum_channel_delta == 1


def test_lsb_rejects_wrong_key() -> None:
    source = _rgba_image()
    payload = WatermarkPayload(PayloadType.DISTRIBUTION, 1, 1, b"D" * 16)
    embedded = LSBWatermarkEngine().embed(source, payload, b"a" * 32)

    result = LSBWatermarkEngine().extract(embedded.image, b"b" * 32, key_versions=[1])

    assert result.valid is False
    assert result.payload is None


def test_lsb_refuses_insufficient_capacity() -> None:
    source = Image.new("RGB", (8, 8), "white")
    payload = WatermarkPayload(PayloadType.OWNERSHIP, 1, 1, b"A" * 16)
    with pytest.raises(CapacityError):
        LSBWatermarkEngine().embed(source, payload, b"k" * 32)
