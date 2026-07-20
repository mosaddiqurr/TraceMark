"""Environment-driven application settings with production safety checks."""

from __future__ import annotations

import os
import secrets
from dataclasses import dataclass, field
from pathlib import Path


def _bool_env(name: str, default: bool) -> bool:
    value = os.getenv(name)
    return default if value is None else value.lower() in {"1", "true", "yes", "on"}


def _csv_env(name: str, default: str) -> tuple[str, ...]:
    return tuple(item.strip() for item in os.getenv(name, default).split(",") if item.strip())


@dataclass(frozen=True, slots=True)
class Settings:
    environment: str = field(default_factory=lambda: os.getenv("TRACEMARK_ENV", "development"))
    database_url: str = field(
        default_factory=lambda: os.getenv(
            "TRACEMARK_DATABASE_URL",
            "postgresql+psycopg://tracemark:tracemark@postgres:5432/tracemark",
        )
    )
    redis_url: str = field(default_factory=lambda: os.getenv("TRACEMARK_REDIS_URL", "redis://redis:6379/0"))
    session_backend: str = field(default_factory=lambda: os.getenv("TRACEMARK_SESSION_BACKEND", "redis"))
    session_pepper: str = field(default_factory=lambda: os.getenv("TRACEMARK_SESSION_PEPPER", ""))
    session_ttl_seconds: int = field(
        default_factory=lambda: int(os.getenv("TRACEMARK_SESSION_TTL_SECONDS", "43200"))
    )
    cookie_name: str = "tracemark_session"
    cookie_secure: bool = field(default_factory=lambda: _bool_env("TRACEMARK_COOKIE_SECURE", False))
    allowed_origins: tuple[str, ...] = field(
        default_factory=lambda: _csv_env("TRACEMARK_ALLOWED_ORIGINS", "http://localhost:5173")
    )
    max_upload_bytes: int = field(default_factory=lambda: int(os.getenv("TRACEMARK_MAX_UPLOAD_BYTES", "26214400")))
    max_image_pixels: int = field(default_factory=lambda: int(os.getenv("TRACEMARK_MAX_IMAGE_PIXELS", "40000000")))
    local_storage_root: Path = field(
        default_factory=lambda: Path(os.getenv("TRACEMARK_STORAGE_ROOT", ".data/objects"))
    )
    storage_backend: str = field(default_factory=lambda: os.getenv("TRACEMARK_STORAGE_BACKEND", "local"))
    minio_endpoint: str = field(default_factory=lambda: os.getenv("TRACEMARK_MINIO_ENDPOINT", "minio:9000"))
    minio_access_key: str = field(default_factory=lambda: os.getenv("TRACEMARK_MINIO_ACCESS_KEY", ""))
    minio_secret_key: str = field(default_factory=lambda: os.getenv("TRACEMARK_MINIO_SECRET_KEY", ""))
    minio_secure: bool = field(default_factory=lambda: _bool_env("TRACEMARK_MINIO_SECURE", False))
    log_level: str = field(default_factory=lambda: os.getenv("TRACEMARK_LOG_LEVEL", "INFO"))
    master_key: str = field(default_factory=lambda: os.getenv("TRACEMARK_MASTER_KEY", "development-only-master-key-change-me"))
    report_key: str = field(default_factory=lambda: os.getenv("TRACEMARK_REPORT_KEY", "development-only-report-key-change-me"))
    scanner_enabled: bool = field(default_factory=lambda: _bool_env("TRACEMARK_SCANNER_ENABLED", True))

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    def validated(self) -> Settings:
        if self.environment not in {"development", "test", "production"}:
            raise ValueError("TRACEMARK_ENV must be development, test, or production")
        if self.session_backend not in {"redis", "memory"}:
            raise ValueError("TRACEMARK_SESSION_BACKEND must be redis or memory")
        if self.is_production and self.session_backend != "redis":
            raise ValueError("production sessions must use Redis")
        if self.is_production and len(self.session_pepper) < 32:
            raise ValueError("TRACEMARK_SESSION_PEPPER must contain at least 32 characters in production")
        if self.is_production and not self.cookie_secure:
            raise ValueError("secure session cookies are mandatory in production")
        if self.is_production and self.storage_backend != "minio":
            raise ValueError("production storage must use the private MinIO backend")
        if self.storage_backend not in {"local", "minio"}:
            raise ValueError("TRACEMARK_STORAGE_BACKEND must be local or minio")
        if self.is_production and (len(self.master_key) < 32 or len(self.report_key) < 32):
            raise ValueError("master and report keys must contain at least 32 characters in production")
        if self.max_upload_bytes <= 0 or self.max_image_pixels <= 0:
            raise ValueError("upload limits must be positive")
        return self


_development_pepper = secrets.token_urlsafe(32)


def load_settings() -> Settings:
    settings = Settings()
    if not settings.session_pepper and not settings.is_production:
        object.__setattr__(settings, "session_pepper", _development_pepper)
    return settings.validated()

