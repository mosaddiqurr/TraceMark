"""Deterministic pixel and perceptual fingerprints."""

from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass

import numpy as np
from PIL import Image


def _dct_matrix(size: int) -> np.ndarray:
    x = np.arange(size, dtype=np.float64)
    k = x[:, None]
    matrix = np.cos(math.pi * (2.0 * x + 1.0) * k / (2.0 * size))
    matrix[0] *= math.sqrt(1.0 / size)
    matrix[1:] *= math.sqrt(2.0 / size)
    return matrix


def _pack_bool(values: np.ndarray) -> int:
    result = 0
    for value in values.reshape(-1):
        result = (result << 1) | int(bool(value))
    return result


def hamming_distance(left: int, right: int) -> int:
    return (left ^ right).bit_count()


def pixel_sha256(image: Image.Image) -> str:
    rgb = image.convert("RGB")
    digest = hashlib.sha256()
    digest.update(rgb.width.to_bytes(4, "big"))
    digest.update(rgb.height.to_bytes(4, "big"))
    digest.update(rgb.tobytes())
    return digest.hexdigest()


def difference_hash(image: Image.Image, hash_size: int = 8) -> int:
    values = np.asarray(
        image.convert("L").resize((hash_size + 1, hash_size), Image.Resampling.LANCZOS),
        dtype=np.int16,
    )
    return _pack_bool(values[:, 1:] > values[:, :-1])


def perceptual_hash(image: Image.Image, hash_size: int = 8, high_frequency_factor: int = 4) -> int:
    sample_size = hash_size * high_frequency_factor
    values = np.asarray(
        image.convert("L").resize((sample_size, sample_size), Image.Resampling.LANCZOS),
        dtype=np.float64,
    )
    dct = _dct_matrix(sample_size)
    frequencies = (dct @ values @ dct.T)[:hash_size, :hash_size]
    comparison = frequencies.copy().reshape(-1)
    threshold = float(np.median(comparison[1:]))
    return _pack_bool(frequencies > threshold)


def wavelet_hash(image: Image.Image, hash_size: int = 8) -> int:
    size = hash_size * 2
    values = np.asarray(
        image.convert("L").resize((size, size), Image.Resampling.LANCZOS),
        dtype=np.float64,
    )
    # One level of the orthonormal Haar low-low band.
    low_rows = (values[:, 0::2] + values[:, 1::2]) / math.sqrt(2.0)
    low_low = (low_rows[0::2, :] + low_rows[1::2, :]) / math.sqrt(2.0)
    return _pack_bool(low_low > float(np.median(low_low)))


def colour_histogram(image: Image.Image, bins: int = 8) -> tuple[float, ...]:
    values = np.asarray(image.convert("RGB"), dtype=np.uint8)
    features: list[float] = []
    for channel in range(3):
        histogram, _ = np.histogram(values[..., channel], bins=bins, range=(0, 256))
        normalizer = max(int(histogram.sum()), 1)
        features.extend(float(value) / normalizer for value in histogram)
    return tuple(features)


@dataclass(frozen=True, slots=True)
class ImageFingerprint:
    pixel_sha256: str
    phash: int
    dhash: int
    whash: int
    colour_histogram: tuple[float, ...]
    width: int
    height: int


def fingerprint(image: Image.Image) -> ImageFingerprint:
    return ImageFingerprint(
        pixel_sha256=pixel_sha256(image),
        phash=perceptual_hash(image),
        dhash=difference_hash(image),
        whash=wavelet_hash(image),
        colour_histogram=colour_histogram(image),
        width=image.width,
        height=image.height,
    )

