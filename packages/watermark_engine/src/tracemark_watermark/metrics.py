"""Measured image-quality evidence used by protection and benchmark workflows."""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass

import numpy as np
from PIL import Image, ImageChops


@dataclass(frozen=True, slots=True)
class ImageQualityMetrics:
    psnr_db: float
    ssim: float
    mean_absolute_error: float
    root_mean_square_error: float
    changed_pixels: int
    changed_pixel_ratio: float
    maximum_channel_delta: int

    def as_dict(self) -> dict[str, float | int]:
        return asdict(self)


def _arrays(reference: Image.Image, candidate: Image.Image) -> tuple[np.ndarray, np.ndarray]:
    if reference.size != candidate.size:
        raise ValueError("quality metrics require images with identical dimensions")
    return (
        np.asarray(reference.convert("RGB"), dtype=np.float64),
        np.asarray(candidate.convert("RGB"), dtype=np.float64),
    )


def _windowed_ssim(left: np.ndarray, right: np.ndarray, window: int = 8) -> float:
    # Standard SSIM constants for 8-bit samples, evaluated over non-overlapping
    # windows to avoid an additional heavyweight signal-processing dependency.
    height, width, _ = left.shape
    scores: list[float] = []
    c1 = (0.01 * 255.0) ** 2
    c2 = (0.03 * 255.0) ** 2
    for row in range(0, height, window):
        for column in range(0, width, window):
            x = left[row : row + window, column : column + window]
            y = right[row : row + window, column : column + window]
            if x.size == 0:
                continue
            mu_x = float(x.mean())
            mu_y = float(y.mean())
            variance_x = float(x.var())
            variance_y = float(y.var())
            covariance = float(((x - mu_x) * (y - mu_y)).mean())
            numerator = (2.0 * mu_x * mu_y + c1) * (2.0 * covariance + c2)
            denominator = (mu_x * mu_x + mu_y * mu_y + c1) * (variance_x + variance_y + c2)
            scores.append(numerator / denominator)
    return float(np.clip(np.mean(scores), -1.0, 1.0))


def measure_quality(reference: Image.Image, candidate: Image.Image) -> ImageQualityMetrics:
    left, right = _arrays(reference, candidate)
    delta = right - left
    squared_error = float(np.mean(delta * delta))
    psnr = math.inf if squared_error == 0.0 else 20.0 * math.log10(255.0 / math.sqrt(squared_error))
    pixel_changed = np.any(delta != 0.0, axis=2)
    return ImageQualityMetrics(
        psnr_db=psnr,
        ssim=_windowed_ssim(left, right),
        mean_absolute_error=float(np.mean(np.abs(delta))),
        root_mean_square_error=math.sqrt(squared_error),
        changed_pixels=int(pixel_changed.sum()),
        changed_pixel_ratio=float(pixel_changed.mean()),
        maximum_channel_delta=int(np.max(np.abs(delta))),
    )


def difference_image(reference: Image.Image, candidate: Image.Image, *, amplify: int = 8) -> Image.Image:
    if reference.size != candidate.size:
        raise ValueError("difference image requires identical dimensions")
    difference = ImageChops.difference(reference.convert("RGB"), candidate.convert("RGB"))
    if amplify <= 1:
        return difference
    values = np.asarray(difference, dtype=np.uint16)
    return Image.fromarray(np.clip(values * amplify, 0, 255).astype(np.uint8), "RGB")
