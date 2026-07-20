from enum import StrEnum


class UserRole(StrEnum):
    USER = "user"
    ADMIN = "admin"


class JobState(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class WatermarkType(StrEnum):
    VISIBLE = "visible"
    LSB = "lsb"
    ROBUST = "robust"


class IntegrityState(StrEnum):
    VALID = "valid"
    INVALID = "invalid"
    NOT_PRESENT = "not_present"
    UNAVAILABLE = "unavailable"


class ProvenanceState(StrEnum):
    VALID = "valid"
    INVALID = "invalid"
    NOT_PRESENT = "not_present"
    UNSUPPORTED = "unsupported"
    VERIFICATION_UNAVAILABLE = "verification_unavailable"


class EvidenceClassification(StrEnum):
    EXACT_REGISTERED_HASH = "exact_registered_hash"
    VALID_DISTRIBUTION_WATERMARK = "valid_distribution_watermark"
    VALID_OWNERSHIP_WATERMARK = "valid_ownership_watermark"
    INVALID_AUTHENTICATED_PAYLOAD = "invalid_authenticated_payload"
    CALIBRATED_VISUAL_DERIVATIVE = "calibrated_visual_derivative"
    POSSIBLE_VISUAL_MATCH = "possible_visual_match"
    NO_EVIDENCE = "no_evidence"
    INCONCLUSIVE = "inconclusive"

