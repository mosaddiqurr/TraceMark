"""Shared engine results and interfaces."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any

from PIL import Image

from .payload import WatermarkPayload


@dataclass(frozen=True, slots=True)
class Capacity:
    available_bits: int
    required_bits: int
    repetitions: int

    @property
    def fits(self) -> bool:
        return self.available_bits >= self.required_bits


@dataclass(frozen=True, slots=True)
class EmbedResult:
    image: Image.Image
    diagnostics: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ExtractionResult:
    valid: bool
    payload: WatermarkPayload | None
    algorithm: str
    key_version: int | None = None
    corrected_symbols: int | None = None
    repetitions_found: int = 0
    bit_reliabilities: tuple[float, ...] = ()
    candidate_transformations: tuple[str, ...] = ()
    integrity_error: str | None = None
    diagnostics: dict[str, Any] = field(default_factory=dict)


class CapacityError(ValueError):
    """The source image cannot safely hold the configured payload."""


class WatermarkEngine(ABC):
    @abstractmethod
    def capacity(self, image: Image.Image) -> Capacity:
        raise NotImplementedError

    @abstractmethod
    def embed(
        self, image: Image.Image, payload: WatermarkPayload, master_key: bytes
    ) -> EmbedResult:
        raise NotImplementedError

    @abstractmethod
    def extract(
        self,
        image: Image.Image,
        master_key: bytes,
        *,
        key_versions: Sequence[int],
    ) -> ExtractionResult:
        raise NotImplementedError

    def diagnostics(self, result: EmbedResult | ExtractionResult) -> dict[str, Any]:
        return dict(result.diagnostics)

