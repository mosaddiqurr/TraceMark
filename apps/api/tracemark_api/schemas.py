"""Version-one API contracts."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from .enums import JobState, UserRole


class ApiModel(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class ErrorDetail(BaseModel):
    code: str
    message: str
    field_errors: dict[str, list[str]] = Field(default_factory=dict)
    correlation_id: str


class ErrorResponse(BaseModel):
    error: ErrorDetail


class UserView(ApiModel):
    id: UUID
    email: str
    display_name: str
    role: UserRole


class RegisterRequest(BaseModel):
    display_name: str = Field(default="TraceMark User", min_length=1, max_length=120)
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=12, max_length=1024)


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=1, max_length=1024)


class SessionResponse(BaseModel):
    user: UserView
    csrf_token: str


class AssetView(ApiModel):
    id: UUID
    name: str = Field(validation_alias="display_name")
    sha256: str
    media_type: str = Field(validation_alias="mime_type")
    width: int
    height: int
    size_bytes: int = Field(validation_alias="byte_size")
    safe_metadata: dict[str, Any]
    perceptual_hashes: dict[str, Any] = Field(validation_alias="fingerprints")
    thumbnail_url: str | None = None
    created_at: datetime


class ProtectedOutputSummary(BaseModel):
    id: UUID
    type: str
    created_at: datetime
    download_url: str
    metrics: dict[str, Any]


class AssetDetail(AssetView):
    protected_outputs: list[ProtectedOutputSummary] = Field(default_factory=list)

class AssetList(BaseModel):
    items: list[AssetView]
    page: int
    page_size: int
    total: int


class JobView(ApiModel):
    id: UUID
    kind: str
    state: JobState
    progress: int
    stage: str
    cancellable: bool
    cancellation_requested: bool
    result_url: str | None
    error_code: str | None
    error_message: str | None
    created_at: datetime
    updated_at: datetime = Field(validation_alias="created_at")
    started_at: datetime | None
    completed_at: datetime | None


class HealthResponse(BaseModel):
    status: str
    database: str | None = None
    sessions: str | None = None


