"""Resolution-independent DWT / DCT / QIM watermark (algorithm version 3).

Version 2 embeds at the submitted resolution, so any resize moves both the
block grid and the size-derived placement key.  Version 3 embeds in a fixed
canonical luminance image instead: the image is resampled to
``CANONICAL_SIZE`` square, the authenticated codeword is quantized into keyed
4x4 DCT coefficients of the canonical LH/HL bands, and the canonical residual
is resampled back and added to the full-resolution luminance.  A few
closed-loop passes compensate for resampling loss.  Extraction resamples any
submitted copy to the same canonical grid, so uniform or non-uniform resizing
is undone before reading.  Cropping still changes the canonical mapping and is
not survived.
"""

from __future__ import annotations

import math
from collections.abc import Sequence

import numpy as np
from PIL import Image

from .crypto import derive_subkey, deterministic_seed
from .models import Capacity, CapacityError, EmbedResult, ExtractionResult, WatermarkEngine
from .payload import CODEWORD_BYTES, PayloadError, WatermarkPayload, decode_payload, encode_payload
from .robust import (
    _bit_array,
    _byte_array,
    _haar_forward,
    _haar_inverse,
    _luminance,
    _replace_luminance,
    _rgb_alpha,
    _to_image,
)

ALGORITHM_VERSION = 3
CANONICAL_SIZE = 256
BLOCK_SIZE = 4
CODEWORD_BITS = CODEWORD_BYTES * 8
MINIMUM_DIMENSION = CANONICAL_SIZE
_COEFFICIENTS = ((1, 2), (2, 1), (1, 1), (2, 2))


def _dct_matrix(size: int) -> np.ndarray:
    matrix = np.empty((size, size), dtype=np.float64)
    for k in range(size):
        scale = math.sqrt(1.0 / size) if k == 0 else math.sqrt(2.0 / size)
        for n in range(size):
            matrix[k, n] = scale * math.cos((2 * n + 1) * k * math.pi / (2.0 * size))
    return matrix


_DCT = _dct_matrix(BLOCK_SIZE)


def _resample(values: np.ndarray, size: tuple[int, int]) -> np.ndarray:
    resized = Image.fromarray(values.astype(np.float32), "F").resize(size, Image.Resampling.BICUBIC)
    return np.asarray(resized, dtype=np.float64)


def _blocks(band: np.ndarray) -> np.ndarray:
    """View a square band as (rows, columns, 4, 4) DCT blocks."""
    count = band.shape[0] // BLOCK_SIZE
    return band.reshape(count, BLOCK_SIZE, count, BLOCK_SIZE).swapaxes(1, 2)


class CanonicalWatermarkEngine(WatermarkEngine):
    name = "canonical-dwt-dct-qim"
    algorithm_version = ALGORITHM_VERSION

    def __init__(self, *, repetitions: int = 4, strength: float = 20.0, passes: int = 5) -> None:
        if repetitions < 1:
            raise ValueError("repetitions must be positive")
        if strength < 8.0:
            raise ValueError("strength below 8 is not reliably recoverable")
        self.repetitions = repetitions
        self.strength = float(strength)
        self.passes = passes

    @staticmethod
    def _available_bits() -> int:
        per_side = (CANONICAL_SIZE // 2) // BLOCK_SIZE
        return 2 * per_side * per_side

    def capacity(self, image: Image.Image) -> Capacity:
        large_enough = min(image.size) >= MINIMUM_DIMENSION
        return Capacity(
            available_bits=self._available_bits() if large_enough else 0,
            required_bits=CODEWORD_BITS * self.repetitions,
            repetitions=self.repetitions,
        )

    def _locations(self, master_key: bytes, key_version: int) -> np.ndarray:
        """Return (repetitions, bits, 4) rows of band, row, column, coefficient index."""
        per_side = (CANONICAL_SIZE // 2) // BLOCK_SIZE
        available = self._available_bits()
        if available < CODEWORD_BITS * self.repetitions:
            raise CapacityError("canonical grid cannot hold the configured repetitions")
        placement_key = derive_subkey(master_key, "canonical-placement", key_version=key_version)
        rng = np.random.default_rng(deterministic_seed(placement_key, b"canonical-dwt-dct-qim/v3"))
        order = rng.permutation(available)[: CODEWORD_BITS * self.repetitions]
        selectors = rng.integers(0, len(_COEFFICIENTS), size=order.size)
        band, rest = np.divmod(order, per_side * per_side)
        row, column = np.divmod(rest, per_side)
        table = np.stack([band, row, column, selectors], axis=1)
        return table.reshape(self.repetitions, CODEWORD_BITS, 4)

    def _steps(self, coefficients: np.ndarray, targets: np.ndarray) -> np.ndarray:
        magnitudes = np.abs(coefficients).reshape(len(coefficients), -1).copy()
        magnitudes[:, 0] = np.nan
        flat_targets = targets[:, 0] * BLOCK_SIZE + targets[:, 1]
        magnitudes[np.arange(len(coefficients)), flat_targets] = np.nan
        activity = np.asarray(np.nanmedian(magnitudes, axis=1), dtype=np.float64)
        return np.asarray(self.strength * (1.0 + np.minimum(activity, 24.0) / 96.0), dtype=np.float64)

    def _gather(self, canonical: np.ndarray, locations: np.ndarray) -> tuple[list[np.ndarray], np.ndarray, np.ndarray]:
        ll, lh, hl, hh = _haar_forward(canonical)
        bands = [lh.copy(), hl.copy(), ll, hh]
        flat = locations.reshape(-1, 4)
        blocks = np.stack(
            [_blocks(bands[int(b)])[int(r), int(c)] for b, r, c, _ in flat],
        )
        coefficients = _DCT @ blocks @ _DCT.T
        targets = np.asarray([_COEFFICIENTS[int(i)] for i in flat[:, 3]])
        return bands, coefficients, targets

    def _embed_canonical(self, canonical: np.ndarray, locations: np.ndarray, bits: np.ndarray) -> np.ndarray:
        bands, coefficients, targets = self._gather(canonical, locations)
        steps = self._steps(coefficients, targets)
        index = np.arange(len(coefficients))
        values = coefficients[index, targets[:, 0], targets[:, 1]]
        scaled = values / steps
        centers = np.rint(scaled)
        wanted = np.tile(bits, self.repetitions)
        wrong = (centers.astype(np.int64) & 1) != wanted
        lower = centers - 1
        upper = centers + 1
        nearer = np.where(np.abs(scaled - lower) <= np.abs(scaled - upper), lower, upper)
        centers = np.where(wrong, nearer, centers)
        coefficients[index, targets[:, 0], targets[:, 1]] = centers * steps
        spatial = _DCT.T @ coefficients @ _DCT
        for (band, row, column, _), block in zip(locations.reshape(-1, 4), spatial, strict=True):
            _blocks(bands[int(band)])[int(row), int(column)] = block
        return _haar_inverse(bands[2], bands[0], bands[1], bands[3])

    def embed(self, image: Image.Image, payload: WatermarkPayload, master_key: bytes) -> EmbedResult:
        capacity = self.capacity(image)
        if not capacity.fits:
            raise CapacityError(f"images must be at least {MINIMUM_DIMENSION} px on each side")
        if payload.algorithm_version != self.algorithm_version:
            raise ValueError("payload algorithm_version does not identify canonical v3")
        rgb, alpha = _rgb_alpha(image)
        original_y = _luminance(rgb)
        locations = self._locations(master_key, payload.key_version)
        bits = _bit_array(encode_payload(payload, master_key))
        canonical_size = (CANONICAL_SIZE, CANONICAL_SIZE)
        watermarked_y = original_y.copy()
        for _ in range(self.passes):
            canonical = _resample(watermarked_y, canonical_size)
            residual = self._embed_canonical(canonical, locations, bits) - canonical
            watermarked_y += _resample(residual, image.size)
        output = _to_image(_replace_luminance(rgb, original_y, watermarked_y), alpha)
        return EmbedResult(
            image=output,
            diagnostics={
                "algorithm": self.name,
                "algorithm_version": self.algorithm_version,
                "embedded_bits": CODEWORD_BITS * self.repetitions,
                "codeword_bits": CODEWORD_BITS,
                "repetitions": self.repetitions,
                "canonical_size": CANONICAL_SIZE,
                "wavelet": "haar-1-level",
                "bands": ("LH", "HL"),
                "block_size": BLOCK_SIZE,
                "strength": self.strength,
            },
        )

    def _read(self, canonical: np.ndarray, locations: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        _, coefficients, targets = self._gather(canonical, locations)
        steps = self._steps(coefficients, targets)
        values = coefficients[np.arange(len(coefficients)), targets[:, 0], targets[:, 1]]
        scaled = values / steps
        bits = (np.rint(scaled).astype(np.int64) & 1).astype(np.uint8)
        reliability = np.clip(1.0 - 2.0 * np.abs(scaled - np.rint(scaled)), 0.0, 1.0)
        shape = (self.repetitions, CODEWORD_BITS)
        return bits.reshape(shape), reliability.reshape(shape)

    def extract(
        self,
        image: Image.Image,
        master_key: bytes,
        *,
        key_versions: Sequence[int],
    ) -> ExtractionResult:
        if min(image.size) < 64:
            return ExtractionResult(
                valid=False, payload=None, algorithm=self.name, integrity_error="insufficient_capacity"
            )
        canonical = _resample(_luminance(_rgb_alpha(image)[0]), (CANONICAL_SIZE, CANONICAL_SIZE))
        attempted: list[str] = []
        last_error = "no_key_versions"
        for key_version in dict.fromkeys(key_versions):
            attempted.append(f"canonical/key:{key_version}")
            bit_matrix, reliability = self._read(canonical, self._locations(master_key, key_version))
            signed = np.where(bit_matrix == 1, 1.0, -1.0)
            voted = ((signed * np.maximum(reliability, 0.05)).sum(axis=0) >= 0.0).astype(np.uint8)
            candidates = [("weighted_vote", voted)]
            candidates.extend((f"repetition:{index}", row) for index, row in enumerate(bit_matrix))
            for source, candidate_bits in candidates:
                try:
                    decoded = decode_payload(_byte_array(candidate_bits), master_key, key_version=key_version)
                except PayloadError as exc:
                    error = "payload_hmac_invalid" if "HMAC validation failed" in str(exc) else type(exc).__name__
                    if error == "payload_hmac_invalid" or last_error != "payload_hmac_invalid":
                        last_error = error
                    continue
                if decoded.payload.algorithm_version != self.algorithm_version:
                    last_error = "algorithm_version_mismatch"
                    continue
                repetitions_found = 0
                for row in bit_matrix:
                    try:
                        decode_payload(_byte_array(row), master_key, key_version=key_version)
                    except PayloadError:
                        continue
                    repetitions_found += 1
                mean_reliability = tuple(float(value) for value in reliability.mean(axis=0))
                return ExtractionResult(
                    valid=True,
                    payload=decoded.payload,
                    algorithm=self.name,
                    key_version=key_version,
                    corrected_symbols=decoded.corrected_symbols,
                    repetitions_found=repetitions_found,
                    bit_reliabilities=mean_reliability,
                    candidate_transformations=tuple(attempted),
                    diagnostics={
                        "accepted_source": source,
                        "mean_bit_reliability": float(np.mean(mean_reliability)),
                        "canonical_size": CANONICAL_SIZE,
                    },
                )
        return ExtractionResult(
            valid=False,
            payload=None,
            algorithm=self.name,
            integrity_error=last_error,
            candidate_transformations=tuple(attempted),
        )
