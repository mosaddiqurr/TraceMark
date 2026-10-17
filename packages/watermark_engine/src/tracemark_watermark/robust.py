"""Blind classical Haar-DWT / block-DCT / QIM watermark engine.

This is a deliberately transparent classical implementation rather than a
wrapper around a third-party watermark product.  It embeds an authenticated
RS(58,38) codeword three times in keyed mid-frequency coefficients of the
luminance LH/HL wavelet bands.
"""

from __future__ import annotations

import math
from collections.abc import Iterable, Sequence
from dataclasses import dataclass

import numpy as np
from PIL import Image

from .crypto import derive_subkey, deterministic_seed
from .models import Capacity, CapacityError, EmbedResult, ExtractionResult, WatermarkEngine
from .payload import CODEWORD_BYTES, PayloadError, WatermarkPayload, decode_payload, encode_payload

ALGORITHM_VERSION = 2
BLOCK_SIZE = 8
CODEWORD_BITS = CODEWORD_BYTES * 8


def _dct_matrix(size: int = BLOCK_SIZE) -> np.ndarray:
    matrix = np.empty((size, size), dtype=np.float64)
    factor = math.pi / (2.0 * size)
    for k in range(size):
        scale = math.sqrt(1.0 / size) if k == 0 else math.sqrt(2.0 / size)
        for n in range(size):
            matrix[k, n] = scale * math.cos((2 * n + 1) * k * factor)
    return matrix


_DCT = _dct_matrix()


def _forward_dct(block: np.ndarray) -> np.ndarray:
    return np.asarray(_DCT @ block @ _DCT.T, dtype=np.float64)


def _inverse_dct(coefficients: np.ndarray) -> np.ndarray:
    return np.asarray(_DCT.T @ coefficients @ _DCT, dtype=np.float64)


def _haar_forward(values: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    a = values[0::2, 0::2]
    b = values[0::2, 1::2]
    c = values[1::2, 0::2]
    d = values[1::2, 1::2]
    return (
        (a + b + c + d) / 2.0,
        (a - b + c - d) / 2.0,
        (a + b - c - d) / 2.0,
        (a - b - c + d) / 2.0,
    )


def _haar_inverse(ll: np.ndarray, lh: np.ndarray, hl: np.ndarray, hh: np.ndarray) -> np.ndarray:
    result = np.empty((ll.shape[0] * 2, ll.shape[1] * 2), dtype=np.float64)
    result[0::2, 0::2] = (ll + lh + hl + hh) / 2.0
    result[0::2, 1::2] = (ll - lh + hl - hh) / 2.0
    result[1::2, 0::2] = (ll + lh - hl - hh) / 2.0
    result[1::2, 1::2] = (ll - lh - hl + hh) / 2.0
    return result


def _rgb_alpha(image: Image.Image) -> tuple[np.ndarray, np.ndarray | None]:
    alpha = None
    if "A" in image.getbands():
        alpha = np.asarray(image.getchannel("A"), dtype=np.uint8).copy()
    return np.asarray(image.convert("RGB"), dtype=np.float64), alpha


def _luminance(rgb: np.ndarray) -> np.ndarray:
    return 0.299 * rgb[..., 0] + 0.587 * rgb[..., 1] + 0.114 * rgb[..., 2]


def _replace_luminance(rgb: np.ndarray, old_y: np.ndarray, new_y: np.ndarray) -> np.ndarray:
    delta = new_y - old_y
    adjusted = rgb + delta[..., None]
    return np.asarray(np.clip(np.rint(adjusted), 0, 255), dtype=np.uint8)


def _to_image(rgb: np.ndarray, alpha: np.ndarray | None) -> Image.Image:
    result = Image.fromarray(rgb, "RGB")
    if alpha is not None:
        result.putalpha(Image.fromarray(alpha, "L"))
    return result


def _bit_array(data: bytes) -> np.ndarray:
    return np.unpackbits(np.frombuffer(data, dtype=np.uint8), bitorder="big")


def _byte_array(bits: np.ndarray) -> bytes:
    return np.packbits(bits.astype(np.uint8), bitorder="big").tobytes()


@dataclass(frozen=True, slots=True)
class _Location:
    band: int
    row: int
    column: int
    coefficient: tuple[int, int]


class RobustWatermarkEngine(WatermarkEngine):
    name = "dwt-dct-qim"
    algorithm_version = ALGORITHM_VERSION

    def __init__(self, *, repetitions: int = 3, strength: float = 32.0) -> None:
        if repetitions < 1:
            raise ValueError("repetitions must be positive")
        if strength < 8.0:
            raise ValueError("strength below 8 is not reliably recoverable")
        self.repetitions = repetitions
        self.strength = float(strength)

    @staticmethod
    def _descriptors(image: Image.Image) -> list[tuple[int, int, int]]:
        band_height = (image.height // 2) // BLOCK_SIZE
        band_width = (image.width // 2) // BLOCK_SIZE
        return [(band, row, column) for band in (0, 1) for row in range(band_height) for column in range(band_width)]

    def capacity(self, image: Image.Image) -> Capacity:
        available = len(self._descriptors(image))
        return Capacity(
            available_bits=available,
            required_bits=CODEWORD_BITS * self.repetitions,
            repetitions=self.repetitions,
        )

    def _locations(
        self,
        image: Image.Image,
        master_key: bytes,
        key_version: int,
    ) -> list[list[_Location]]:
        descriptors = self._descriptors(image)
        placement_key = derive_subkey(master_key, "robust-placement", key_version=key_version)
        geometry = image.width.to_bytes(4, "big") + image.height.to_bytes(4, "big")
        used: set[tuple[int, int, int]] = set()
        repetitions: list[list[_Location]] = []
        coefficients = ((2, 3), (3, 2), (2, 4), (4, 2))
        for repetition in range(self.repetitions):
            context = b"dwt-dct-qim/v1/" + geometry + repetition.to_bytes(2, "big")
            rng = np.random.default_rng(deterministic_seed(placement_key, context))
            order = rng.permutation(len(descriptors))
            selected: list[_Location] = []
            for raw_index in order:
                descriptor = descriptors[int(raw_index)]
                if descriptor in used:
                    continue
                used.add(descriptor)
                selector = int(rng.integers(0, len(coefficients)))
                selected.append(_Location(*descriptor, coefficients[selector]))
                if len(selected) == CODEWORD_BITS:
                    break
            if len(selected) != CODEWORD_BITS:
                raise CapacityError("not enough distinct DWT blocks for configured repetitions")
            repetitions.append(selected)
        return repetitions

    def _quantization_step(self, coefficients: np.ndarray, target: tuple[int, int]) -> float:
        mask = np.ones(coefficients.shape, dtype=bool)
        mask[0:2, 0:2] = False
        mask[target] = False
        activity = float(np.median(np.abs(coefficients[mask])))
        return self.strength * (1.0 + min(activity, 24.0) / 96.0)

    @staticmethod
    def _embed_bit(coefficient: float, step: float, bit: int) -> float:
        scaled = coefficient / step
        center = int(round(scaled))
        if (center & 1) != bit:
            lower = center - 1
            upper = center + 1
            center = lower if abs(scaled - lower) <= abs(scaled - upper) else upper
        return center * step

    def _embed_locations(
        self,
        bands: list[np.ndarray],
        locations: Iterable[_Location],
        bits: np.ndarray,
    ) -> None:
        for location, bit in zip(locations, bits, strict=True):
            row = location.row * BLOCK_SIZE
            column = location.column * BLOCK_SIZE
            block = bands[location.band][row : row + BLOCK_SIZE, column : column + BLOCK_SIZE]
            coefficients = _forward_dct(block)
            step = self._quantization_step(coefficients, location.coefficient)
            coefficients[location.coefficient] = self._embed_bit(
                float(coefficients[location.coefficient]), step, int(bit)
            )
            block[:] = _inverse_dct(coefficients)

    def embed(self, image: Image.Image, payload: WatermarkPayload, master_key: bytes) -> EmbedResult:
        capacity = self.capacity(image)
        if not capacity.fits:
            raise CapacityError(
                f"image has {capacity.available_bits} eligible DWT blocks; {capacity.required_bits} are required"
            )
        if payload.algorithm_version != self.algorithm_version:
            raise ValueError("payload algorithm_version does not identify robust v2")
        rgb, alpha = _rgb_alpha(image)
        original_y = _luminance(rgb)
        even_height = image.height - image.height % 2
        even_width = image.width - image.width % 2
        ll, lh, hl, hh = _haar_forward(original_y[:even_height, :even_width])
        bands = [lh.copy(), hl.copy()]
        locations = self._locations(image, master_key, payload.key_version)
        bits = _bit_array(encode_payload(payload, master_key))
        for repetition_locations in locations:
            self._embed_locations(bands, repetition_locations, bits)
        rebuilt = _haar_inverse(ll, bands[0], bands[1], hh)
        watermarked_y = original_y.copy()
        watermarked_y[:even_height, :even_width] = rebuilt
        output = _to_image(_replace_luminance(rgb, original_y, watermarked_y), alpha)
        return EmbedResult(
            image=output,
            diagnostics={
                "algorithm": self.name,
                "algorithm_version": self.algorithm_version,
                "embedded_bits": CODEWORD_BITS * self.repetitions,
                "codeword_bits": CODEWORD_BITS,
                "repetitions": self.repetitions,
                "wavelet": "haar-1-level",
                "bands": ("LH", "HL"),
                "block_size": BLOCK_SIZE,
                "strength": self.strength,
            },
        )

    def _read_locations(self, bands: list[np.ndarray], locations: Iterable[_Location]) -> tuple[np.ndarray, np.ndarray]:
        bits: list[int] = []
        reliability: list[float] = []
        for location in locations:
            row = location.row * BLOCK_SIZE
            column = location.column * BLOCK_SIZE
            block = bands[location.band][row : row + BLOCK_SIZE, column : column + BLOCK_SIZE]
            coefficients = _forward_dct(block)
            step = self._quantization_step(coefficients, location.coefficient)
            scaled = float(coefficients[location.coefficient]) / step
            bits.append(int(round(scaled)) & 1)
            reliability.append(max(0.0, min(1.0, 1.0 - 2.0 * abs(scaled - round(scaled)))))
        return np.asarray(bits, dtype=np.uint8), np.asarray(reliability, dtype=np.float64)

    @staticmethod
    def _candidate_images(image: Image.Image) -> Iterable[tuple[str, Image.Image]]:
        # The bounded candidates are intentionally small; this is synchronization
        # assistance, not an unbounded geometric attack search.
        yield "identity", image
        for angle in (-1.0, 1.0):
            yield f"rotation:{angle:+.1f}", image.rotate(angle, resample=Image.Resampling.BICUBIC)
        width, height = image.size
        center = (width / 2.0, height / 2.0)
        for scale in (0.99, 1.01):
            inverse = 1.0 / scale
            a = inverse
            e = inverse
            c = center[0] * (1.0 - inverse)
            f = center[1] * (1.0 - inverse)
            yield (
                f"scale:{scale:.2f}",
                image.transform(
                    image.size,
                    Image.Transform.AFFINE,
                    (a, 0.0, c, 0.0, e, f),
                    resample=Image.Resampling.BICUBIC,
                ),
            )
        for x, y in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            yield (
                f"offset:{x:+d},{y:+d}",
                image.transform(
                    image.size,
                    Image.Transform.AFFINE,
                    (1.0, 0.0, float(x), 0.0, 1.0, float(y)),
                    resample=Image.Resampling.BICUBIC,
                ),
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
        attempted: list[str] = []
        last_error = "no_key_versions"
        for transformation, candidate in self._candidate_images(image):
            candidate_y = _luminance(_rgb_alpha(candidate)[0])
            even_height = candidate.height - candidate.height % 2
            even_width = candidate.width - candidate.width % 2
            _, lh, hl, _ = _haar_forward(candidate_y[:even_height, :even_width])
            bands = [lh, hl]
            for key_version in dict.fromkeys(key_versions):
                attempted.append(f"{transformation}/key:{key_version}")
                locations = self._locations(candidate, master_key, key_version)
                repeat_bits: list[np.ndarray] = []
                repeat_reliability: list[np.ndarray] = []
                for repetition_locations in locations:
                    bits, reliability = self._read_locations(bands, repetition_locations)
                    repeat_bits.append(bits)
                    repeat_reliability.append(reliability)
                bit_matrix = np.stack(repeat_bits)
                reliability_matrix = np.stack(repeat_reliability)
                signed = np.where(bit_matrix == 1, 1.0, -1.0)
                weights = np.maximum(reliability_matrix, 0.05)
                voted = ((signed * weights).sum(axis=0) >= 0.0).astype(np.uint8)

                candidates = [("weighted_vote", voted)]
                candidates.extend((f"repetition:{index}", value) for index, value in enumerate(repeat_bits))
                for source, candidate_bits in candidates:
                    try:
                        decoded = decode_payload(
                            _byte_array(candidate_bits),
                            master_key,
                            key_version=key_version,
                        )
                    except PayloadError as exc:
                        candidate_error = (
                            "payload_hmac_invalid" if "HMAC validation failed" in str(exc) else type(exc).__name__
                        )
                        if candidate_error == "payload_hmac_invalid" or last_error != "payload_hmac_invalid":
                            last_error = candidate_error
                        continue
                    if decoded.payload.algorithm_version != self.algorithm_version:
                        last_error = "algorithm_version_mismatch"
                        continue
                    repetitions_found = 0
                    for individual in repeat_bits:
                        try:
                            decode_payload(
                                _byte_array(individual),
                                master_key,
                                key_version=key_version,
                            )
                        except PayloadError:
                            pass
                        else:
                            repetitions_found += 1
                    mean_reliability = tuple(float(value) for value in reliability_matrix.mean(axis=0))
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
                            "candidate_count": len(attempted),
                        },
                    )
        return ExtractionResult(
            valid=False,
            payload=None,
            algorithm=self.name,
            integrity_error=last_error,
            candidate_transformations=tuple(attempted),
            diagnostics={"candidate_count": len(attempted)},
        )
