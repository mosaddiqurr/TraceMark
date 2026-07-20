"""Relational metadata models. Binary image data never enters the database."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import JSON, Boolean, DateTime, Enum, Float, ForeignKey, Index, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base
from .enums import (
    EvidenceClassification,
    IntegrityState,
    JobState,
    ProvenanceState,
    UserRole,
    WatermarkType,
)


def now_utc() -> datetime:
    return datetime.now(UTC)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=now_utc, onupdate=now_utc, nullable=False
    )


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(120), nullable=False, default="TraceMark User")
    password_hash: Mapped[str] = mapped_column(String(512), nullable=False)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole, native_enum=False), default=UserRole.USER, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class UserSession(Base):
    """Audit metadata only; live opaque session values remain in Redis."""

    __tablename__ = "user_sessions"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    token_digest: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ip_hint: Mapped[str | None] = mapped_column(String(64))
    user_agent_hint: Mapped[str | None] = mapped_column(String(160))


class Asset(Base, TimestampMixin):
    __tablename__ = "assets"
    __table_args__ = (Index("ix_assets_owner_created", "owner_id", "created_at"),)

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    owner_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    original_object_key: Mapped[str] = mapped_column(String(512), unique=True, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    mime_type: Mapped[str] = mapped_column(String(64), nullable=False)
    width: Mapped[int] = mapped_column(Integer, nullable=False)
    height: Mapped[int] = mapped_column(Integer, nullable=False)
    byte_size: Mapped[int] = mapped_column(Integer, nullable=False)
    safe_metadata: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    fingerprints: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)


class WatermarkProfile(Base, TimestampMixin):
    __tablename__ = "watermark_profiles"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    owner_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    watermark_type: Mapped[WatermarkType] = mapped_column(Enum(WatermarkType, native_enum=False), nullable=False)
    parameters: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)


class ProtectedOutput(Base, TimestampMixin):
    __tablename__ = "protected_outputs"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    owner_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    asset_id: Mapped[UUID] = mapped_column(ForeignKey("assets.id", ondelete="CASCADE"), index=True)
    profile_id: Mapped[UUID | None] = mapped_column(ForeignKey("watermark_profiles.id", ondelete="SET NULL"))
    token: Mapped[UUID] = mapped_column(Uuid, unique=True, default=uuid4, nullable=False)
    algorithm_version: Mapped[int] = mapped_column(Integer, nullable=False)
    key_version: Mapped[int] = mapped_column(Integer, nullable=False)
    object_key: Mapped[str] = mapped_column(String(512), unique=True, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    metrics: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)


class DistributionCopy(Base, TimestampMixin):
    __tablename__ = "distribution_copies"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    owner_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    protected_output_id: Mapped[UUID] = mapped_column(
        ForeignKey("protected_outputs.id", ondelete="CASCADE"), index=True
    )
    token: Mapped[UUID] = mapped_column(Uuid, unique=True, default=uuid4, nullable=False)
    recipient_label: Mapped[str | None] = mapped_column(String(255))
    reference: Mapped[str | None] = mapped_column(String(255))
    object_key: Mapped[str] = mapped_column(String(512), unique=True, nullable=False)
    download_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_downloaded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Job(Base):
    __tablename__ = "jobs"
    __table_args__ = (Index("ix_jobs_owner_created", "owner_id", "created_at"),)

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    owner_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    kind: Mapped[str] = mapped_column(String(64), nullable=False)
    state: Mapped[JobState] = mapped_column(Enum(JobState, native_enum=False), default=JobState.QUEUED)
    progress: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    stage: Mapped[str] = mapped_column(String(120), default="queued", nullable=False)
    cancellable: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    cancellation_requested: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    result_url: Mapped[str | None] = mapped_column(String(512))
    error_code: Mapped[str | None] = mapped_column(String(80))
    error_message: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class VerificationEvidence(Base):
    __tablename__ = "verification_evidence"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    owner_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    classification: Mapped[EvidenceClassification] = mapped_column(
        Enum(EvidenceClassification, native_enum=False), nullable=False
    )
    integrity_state: Mapped[IntegrityState] = mapped_column(Enum(IntegrityState, native_enum=False))
    provenance_state: Mapped[ProvenanceState] = mapped_column(Enum(ProvenanceState, native_enum=False))
    evidence_schema_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    evidence: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    submitted_sha256: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, nullable=False)


class Collection(Base, TimestampMixin):
    __tablename__ = "collections"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    owner_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)


class IndexedMedia(Base):
    __tablename__ = "indexed_media"
    __table_args__ = (Index("ix_indexed_collection_sha", "collection_id", "sha256", unique=True),)

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    owner_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    collection_id: Mapped[UUID] = mapped_column(ForeignKey("collections.id", ondelete="CASCADE"), index=True)
    object_key: Mapped[str] = mapped_column(String(512), unique=True, nullable=False)
    thumbnail_object_key: Mapped[str | None] = mapped_column(String(512), unique=True)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    fingerprints: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    source_label: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, nullable=False)


class ScanSource(Base):
    __tablename__ = "scan_sources"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    owner_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    submitted_url: Mapped[str] = mapped_column(Text, nullable=False)
    final_url: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(64), nullable=False)
    robots_allowed: Mapped[bool | None] = mapped_column(Boolean)
    candidate_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    evidence: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, nullable=False)


class BenchmarkRun(Base):
    __tablename__ = "benchmark_runs"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    owner_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    profile: Mapped[str] = mapped_column(String(64), nullable=False)
    seed: Mapped[int] = mapped_column(Integer, nullable=False)
    state: Mapped[JobState] = mapped_column(Enum(JobState, native_enum=False), default=JobState.QUEUED)
    configuration: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class BenchmarkResult(Base):
    __tablename__ = "benchmark_results"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    run_id: Mapped[UUID] = mapped_column(ForeignKey("benchmark_runs.id", ondelete="CASCADE"), index=True)
    transformation: Mapped[str] = mapped_column(String(120), nullable=False)
    parameters: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    detected: Mapped[bool] = mapped_column(Boolean, nullable=False)
    metrics: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    artifact_object_key: Mapped[str | None] = mapped_column(String(512))
    duration_ms: Mapped[float] = mapped_column(Float, nullable=False)


class Report(Base):
    __tablename__ = "reports"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    owner_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    kind: Mapped[str] = mapped_column(String(64), nullable=False)
    evidence_schema_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    evidence_snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    evidence_hmac: Mapped[str] = mapped_column(String(128), nullable=False)
    object_keys: Mapped[dict[str, str]] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, nullable=False)


class KeyVersion(Base):
    __tablename__ = "key_versions"

    version: Mapped[int] = mapped_column(Integer, primary_key=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    activated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, nullable=False)
    retired_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AuditEvent(Base):
    __tablename__ = "audit_events"
    __table_args__ = (Index("ix_audit_actor_created", "actor_user_id", "created_at"),)

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    actor_user_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(80), nullable=False)
    resource_id: Mapped[UUID | None] = mapped_column(Uuid)
    correlation_id: Mapped[str] = mapped_column(String(64), nullable=False)
    details: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, nullable=False)

