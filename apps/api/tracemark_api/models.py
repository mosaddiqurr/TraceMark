"""Only anonymous workspace capabilities and private trace descriptors persist."""

from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import JSON, Float, ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


class Workspace(Base):
    __tablename__ = "browser_workspaces"
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    token_digest: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    csrf_token: Mapped[str] = mapped_column(String(64), nullable=False)
    expires_at: Mapped[float] = mapped_column(Float, index=True, nullable=False)


class Trace(Base):
    __tablename__ = "image_traces"
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    owner_id: Mapped[UUID] = mapped_column(ForeignKey("browser_workspaces.id", ondelete="CASCADE"), index=True)
    source_name: Mapped[str] = mapped_column(String(255), nullable=False)
    reference_label: Mapped[str | None] = mapped_column(String(120))
    payload_type: Mapped[str] = mapped_column(String(16), nullable=False)
    source_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    output_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    descriptor: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[float] = mapped_column(Float, nullable=False)
