"""Educational fragile least-significant-bit watermark baseline."""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
from PIL import Image

from .crypto import derive_subkey, deterministic_seed
from .models import Capacity, CapacityError, EmbedResult, ExtractionResult, WatermarkEngine
from .payload import (
    CODEWORD_BYTES,
    PayloadError,
    WatermarkPayload,
    decode_payload,
    encode_payload,
)

ALGORITHM_VERSION = 1
_REQUIRED_BITS = CODEWORD_BYTES * 8


def _bits(data: bytes) -> np.ndarray:
    return np.unpackbits(np.frombuffer(data, dtype=np.uint8), bitorder="big")


def _bytes(bits: np.ndarray) -> bytes:
    return np.packbits(bits.astype(np.uint8), bitorder="big").tobytes()


def _rgb_and_alpha(image: Image.Image) -> tuple[np.ndarray, np.ndarray | None]:
    alpha = None
    if "A" in image.getbands():
        alpha = np.asarray(image.getchannel("A"), dtype=np.uint8).copy()
    rgb = np.asarray(image.convert("RGB"), dtype=np.uint8).copy()
    return rgb, alpha


def _to_image(rgb: np.ndarray, alpha: np.ndarray | None) -> Image.Image:
    result = Image.fromarray(rgb.astype(np.uint8), "RGB")
    if alpha is not None:
        result.putalpha(Image.fromarray(alpha, "L"))
    return result


class LSBWatermarkEngine(WatermarkEngine):
    """Blind authenticated LSB implementation.

    This engine is intentionally a fragility baseline.  Recompression, resizing,
    colour conversion, or routine image editing is expected to destroy it.
    """

    name = "lsb"
    algorithm_version = ALGORITHM_VERSION

    def capacity(self, image: Image.Image) -> Capacity:
        width, height = image.size
        return Capacity(
            available_bits=width * height * 3,
            required_bits=_REQUIRED_BITS,
            repetitions=1,
        )

    @staticmethod
    def _positions(
        master_key: bytes,
        key_version: int,
        width: int,
        height: int,
    ) -> np.ndarray:
        placement_key = derive_subkey(master_key, "lsb-placement", key_version=key_version)
        context = b"lsb/v1/" + width.to_bytes(4, "big") + height.to_bytes(4, "big")
        rng = np.random.default_rng(deterministic_seed(placement_key, context))
        return rng.choice(width * height * 3, size=_REQUIRED_BITS, replace=False)

    def embed(self, image: Image.Image, payload: WatermarkPayload, master_key: bytes) -> EmbedResult:
        capacity = self.capacity(image)
        if not capacity.fits:
            raise CapacityError(
                f"image has {capacity.available_bits} writable bits; {capacity.required_bits} are required"
            )
        if payload.algorithm_version != self.algorithm_version:
            raise ValueError("payload algorithm_version does not identify LSB v1")
        rgb, alpha = _rgb_and_alpha(image)
        flat = rgb.reshape(-1)
        positions = self._positions(master_key, payload.key_version, image.width, image.height)
        payload_bits = _bits(encode_payload(payload, master_key))
        flat[positions] = (flat[positions] & 0xFE) | payload_bits
        return EmbedResult(
            image=_to_image(rgb, alpha),
            diagnostics={
                "algorithm": self.name,
                "algorithm_version": self.algorithm_version,
                "embedded_bits": int(payload_bits.size),
                "repetitions": 1,
                "fragile": True,
                "warning": "LSB watermarks are not expected to survive recompression or resizing.",
            },
        )

    def extract(
        self,
        image: Image.Image,
        master_key: bytes,
        *,
        key_versions: Sequence[int],
    ) -> ExtractionResult:
        if not self.capacity(image).fits:
            return ExtractionResult(
                valid=False,
                payload=None,
                algorithm=self.name,
                integrity_error="insufficient_capacity",
            )
        rgb, _ = _rgb_and_alpha(image)
        flat = rgb.reshape(-1)
        errors: list[str] = []
        for key_version in dict.fromkeys(key_versions):
            positions = self._positions(master_key, key_version, image.width, image.height)
            codeword = _bytes(flat[positions] & 1)
            try:
                decoded = decode_payload(codeword, master_key, key_version=key_version)
            except PayloadError as exc:
                errors.append("payload_hmac_invalid" if "HMAC validation failed" in str(exc) else type(exc).__name__)
                continue
            if decoded.payload.algorithm_version != self.algorithm_version:
                errors.append("algorithm_version_mismatch")
                continue
            return ExtractionResult(
                valid=True,
                payload=decoded.payload,
                algorithm=self.name,
                key_version=key_version,
                corrected_symbols=decoded.corrected_symbols,
                repetitions_found=1,
                bit_reliabilities=(1.0,) * _REQUIRED_BITS,
                candidate_transformations=("identity",),
                diagnostics={"fragile": True, "candidate_key_versions": len(errors) + 1},
            )
        return ExtractionResult(
            valid=False,
            payload=None,
            algorithm=self.name,
            integrity_error=errors[-1] if errors else "no_key_versions",
            candidate_transformations=("identity",),
            diagnostics={"candidate_errors": tuple(errors)},
        )
