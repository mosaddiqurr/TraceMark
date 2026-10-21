"""TraceMark's framework-independent still-image forensic engine."""

from .canonical import CanonicalWatermarkEngine
from .crypto import KeyMaterialError, derive_subkey, hkdf_sha256
from .fingerprints import ImageFingerprint, fingerprint, hamming_distance
from .lsb import LSBWatermarkEngine
from .matching import ClassicalSimilarityEngine, SimilarityEngine, SimilarityEvidence
from .metrics import ImageQualityMetrics, difference_image, measure_quality
from .models import Capacity, CapacityError, EmbedResult, ExtractionResult, WatermarkEngine
from .payload import (
    CODEWORD_BYTES,
    RAW_PAYLOAD_BYTES,
    DecodedPayload,
    PayloadCorrectionError,
    PayloadError,
    PayloadIntegrityError,
    PayloadType,
    WatermarkPayload,
    decode_payload,
    encode_payload,
)
from .provenance import C2PAProvenanceAdapter, ProvenanceAdapter, ProvenanceResult, ProvenanceState
from .robust import RobustWatermarkEngine
from .visible import VisibleWatermarkOptions, add_visible_logo, add_visible_text

__all__ = [
    "CODEWORD_BYTES",
    "RAW_PAYLOAD_BYTES",
    "C2PAProvenanceAdapter",
    "CanonicalWatermarkEngine",
    "Capacity",
    "CapacityError",
    "ClassicalSimilarityEngine",
    "DecodedPayload",
    "EmbedResult",
    "ExtractionResult",
    "ImageFingerprint",
    "ImageQualityMetrics",
    "KeyMaterialError",
    "LSBWatermarkEngine",
    "PayloadCorrectionError",
    "PayloadError",
    "PayloadIntegrityError",
    "PayloadType",
    "ProvenanceAdapter",
    "ProvenanceResult",
    "ProvenanceState",
    "RobustWatermarkEngine",
    "SimilarityEngine",
    "SimilarityEvidence",
    "VisibleWatermarkOptions",
    "WatermarkEngine",
    "WatermarkPayload",
    "add_visible_logo",
    "add_visible_text",
    "decode_payload",
    "derive_subkey",
    "difference_image",
    "encode_payload",
    "fingerprint",
    "hamming_distance",
    "hkdf_sha256",
    "measure_quality",
]
