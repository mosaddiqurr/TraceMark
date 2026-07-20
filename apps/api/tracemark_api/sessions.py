"""Opaque, revocable server-side sessions with independent CSRF secrets."""

from __future__ import annotations

import hashlib
import hmac
import json
import secrets
import time
from dataclasses import asdict, dataclass
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True, slots=True)
class SessionRecord:
    user_id: str
    csrf_digest: str
    csrf_token: str
    created_at: int
    expires_at: int


class SessionBackend(Protocol):
    async def set(self, key: str, value: str, ttl_seconds: int) -> None: ...
    async def get(self, key: str) -> str | None: ...
    async def delete(self, key: str) -> None: ...


class RedisSessionBackend:
    def __init__(self, client: object):
        self.client = client

    async def set(self, key: str, value: str, ttl_seconds: int) -> None:
        await self.client.set(key, value, ex=ttl_seconds)  # type: ignore[attr-defined]

    async def get(self, key: str) -> str | None:
        value = await self.client.get(key)  # type: ignore[attr-defined]
        if value is None:
            return None
        return value.decode() if isinstance(value, bytes) else str(value)

    async def delete(self, key: str) -> None:
        await self.client.delete(key)  # type: ignore[attr-defined]


class MemorySessionBackend:
    """Test/development backend; production startup rejects its use."""

    def __init__(self) -> None:
        self._data: dict[str, tuple[str, int]] = {}

    async def set(self, key: str, value: str, ttl_seconds: int) -> None:
        self._data[key] = (value, int(time.time()) + ttl_seconds)

    async def get(self, key: str) -> str | None:
        item = self._data.get(key)
        if item is None:
            return None
        if item[1] <= int(time.time()):
            self._data.pop(key, None)
            return None
        return item[0]

    async def delete(self, key: str) -> None:
        self._data.pop(key, None)


class SessionManager:
    def __init__(self, backend: SessionBackend, pepper: str, ttl_seconds: int = 43200):
        if len(pepper) < 32:
            raise ValueError("session pepper must contain at least 32 characters")
        self.backend = backend
        self._pepper = pepper.encode()
        self.ttl_seconds = ttl_seconds

    def token_digest(self, token: str) -> str:
        return hmac.new(self._pepper, token.encode(), hashlib.sha256).hexdigest()

    def csrf_digest(self, csrf_token: str) -> str:
        return hmac.new(self._pepper, b"csrf:" + csrf_token.encode(), hashlib.sha256).hexdigest()

    async def create(self, user_id: UUID) -> tuple[str, str, SessionRecord]:
        token = secrets.token_urlsafe(32)
        csrf_token = secrets.token_urlsafe(32)
        now = int(time.time())
        record = SessionRecord(
            user_id=str(user_id),
            csrf_digest=self.csrf_digest(csrf_token),
            csrf_token=csrf_token,
            created_at=now,
            expires_at=now + self.ttl_seconds,
        )
        await self.backend.set(self.token_digest(token), json.dumps(asdict(record)), self.ttl_seconds)
        return token, csrf_token, record

    async def resolve(self, token: str | None) -> SessionRecord | None:
        if not token:
            return None
        raw = await self.backend.get(self.token_digest(token))
        if raw is None:
            return None
        try:
            record = SessionRecord(**json.loads(raw))
        except (TypeError, ValueError, json.JSONDecodeError):
            return None
        if record.expires_at <= int(time.time()):
            await self.delete(token)
            return None
        return record

    def verify_csrf(self, record: SessionRecord, csrf_token: str | None) -> bool:
        if not csrf_token:
            return False
        return hmac.compare_digest(record.csrf_digest, self.csrf_digest(csrf_token))

    async def delete(self, token: str | None) -> None:
        if token:
            await self.backend.delete(self.token_digest(token))

    async def rotate(self, token: str, user_id: UUID) -> tuple[str, str, SessionRecord]:
        await self.delete(token)
        return await self.create(user_id)

