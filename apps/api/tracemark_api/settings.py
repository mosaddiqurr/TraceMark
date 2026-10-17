"""Small environment-configured deployment with fail-closed production keys."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlsplit


def _bool(name: str, default: bool = False) -> bool:
    return os.getenv(name, str(default)).lower() in {"1", "true", "yes"}


@dataclass(frozen=True, slots=True)
class Settings:
    environment: str = field(default_factory=lambda: os.getenv("TRACEMARK_ENV", "development"))
    data_root: Path = field(default_factory=lambda: Path(os.getenv("TRACEMARK_DATA_ROOT", ".data/focused")))
    database_url: str = ""  # Tests may supply a separate SQLite database.
    allowed_origins: tuple[str, ...] = field(
        default_factory=lambda: tuple(
            x.strip()
            for x in os.getenv(
                "TRACEMARK_ALLOWED_ORIGINS",
                "http://localhost:5173,http://127.0.0.1:5173",
            ).split(",")
            if x.strip()
        )
    )
    cookie_name: str = "tracemark_workspace"
    cookie_secure: bool = field(default_factory=lambda: _bool("TRACEMARK_COOKIE_SECURE"))
    cookie_samesite: str = field(default_factory=lambda: os.getenv("TRACEMARK_COOKIE_SAMESITE", "lax"))
    session_ttl_seconds: int = field(default_factory=lambda: int(os.getenv("TRACEMARK_RETENTION_SECONDS", "2592000")))
    max_upload_bytes: int = field(default_factory=lambda: int(os.getenv("TRACEMARK_MAX_UPLOAD_BYTES", "20971520")))
    max_image_pixels: int = field(default_factory=lambda: int(os.getenv("TRACEMARK_MAX_IMAGE_PIXELS", "4000000")))
    max_image_dimension: int = field(default_factory=lambda: int(os.getenv("TRACEMARK_MAX_IMAGE_DIMENSION", "4096")))
    processing_timeout_seconds: float = field(
        default_factory=lambda: float(os.getenv("TRACEMARK_PROCESSING_TIMEOUT", "30"))
    )
    processing_concurrency: int = field(default_factory=lambda: int(os.getenv("TRACEMARK_PROCESSING_CONCURRENCY", "1")))
    output_ttl_seconds: int = field(default_factory=lambda: int(os.getenv("TRACEMARK_OUTPUT_TTL_SECONDS", "900")))
    transient_max_bytes: int = field(
        default_factory=lambda: int(os.getenv("TRACEMARK_TRANSIENT_MAX_BYTES", "134217728"))
    )
    max_workspace_traces: int = 100
    max_workspaces: int = 1000
    max_traces: int = 10000
    processing_rate_limit: int = field(default_factory=lambda: int(os.getenv("TRACEMARK_PROCESSING_RATE_LIMIT", "30")))
    master_key: str = field(
        default_factory=lambda: os.getenv("TRACEMARK_MASTER_KEY", "development-master-key-do-not-deploy")
    )
    report_key: str = field(
        default_factory=lambda: os.getenv("TRACEMARK_REPORT_KEY", "development-report-key-do-not-deploy")
    )
    session_pepper: str = field(
        default_factory=lambda: os.getenv("TRACEMARK_SESSION_PEPPER", "development-session-key-do-not-deploy")
    )
    log_level: str = field(default_factory=lambda: os.getenv("TRACEMARK_LOG_LEVEL", "INFO"))

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @property
    def sqlite_url(self) -> str:
        return self.database_url or f"sqlite:///{(self.data_root / 'registry.sqlite3').resolve().as_posix()}"

    def validated(self) -> Settings:
        if self.environment not in {"development", "test", "production"}:
            raise ValueError("TRACEMARK_ENV must be development, test, or production")
        if not self.sqlite_url.startswith("sqlite:///"):
            raise ValueError("the focused deployment uses SQLite in a persistent private directory")
        if self.cookie_samesite not in {"lax", "strict", "none"}:
            raise ValueError("invalid cookie SameSite setting")
        if self.cookie_samesite == "none" and not self.cookie_secure:
            raise ValueError("SameSite=None requires secure cookies")
        if not self.allowed_origins:
            raise ValueError("at least one exact frontend origin is required")
        for origin in self.allowed_origins:
            parsed = urlsplit(origin)
            if (
                parsed.scheme not in {"http", "https"}
                or not parsed.netloc
                or parsed.path
                or parsed.query
                or parsed.fragment
                or parsed.username
                or "*" in origin
            ):
                raise ValueError("CORS origins must be exact HTTP(S) origins without paths or wildcards")
            if self.is_production and parsed.scheme != "https":
                raise ValueError("production frontend origins must use HTTPS")
        keys = (self.master_key, self.report_key, self.session_pepper)
        if any(len(key) < 32 for key in keys) or len(set(keys)) != 3:
            raise ValueError("three distinct keys of at least 32 characters are required")
        if self.is_production and (not self.cookie_secure or any(key.startswith("development-") for key in keys)):
            raise ValueError("production requires secure cookies and independently generated secrets")
        if not 60 <= self.session_ttl_seconds <= 7776000:
            raise ValueError("metadata retention must be between one minute and 90 days")
        if not 1 <= self.processing_concurrency <= 4 or not 0 < self.processing_timeout_seconds <= 120:
            raise ValueError("processing concurrency/time limits are outside supported bounds")
        if not 1 <= self.max_upload_bytes <= 32 * 1024 * 1024 or not 1 <= self.max_image_pixels <= 8_000_000:
            raise ValueError("upload limits are outside supported bounds")
        if not 1 <= self.max_image_dimension <= 8192 or not 1 <= self.output_ttl_seconds <= 3600:
            raise ValueError("dimension/download expiry limits are outside supported bounds")
        if self.transient_max_bytes < self.max_upload_bytes or self.processing_rate_limit < 1:
            raise ValueError("transient storage/rate limits are invalid")
        return self


def load_settings() -> Settings:
    return Settings().validated()
