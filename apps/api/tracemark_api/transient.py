"""Private TTL-bounded memory artifacts; images and reports never reach disk."""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from uuid import UUID, uuid4


@dataclass(frozen=True, slots=True)
class Artifact:
    owner_id: UUID
    content: bytes
    mime_type: str
    expires_at: float


class TransientStore:
    def __init__(self, max_bytes: int, ttl_seconds: int):
        self.max_bytes = max_bytes
        self.ttl_seconds = ttl_seconds
        self._items: dict[UUID, Artifact] = {}
        self._lock = threading.RLock()

    def prune(self) -> None:
        with self._lock:
            self._items = {k: v for k, v in self._items.items() if v.expires_at > time.monotonic()}

    def put(self, owner_id: UUID, content: bytes, mime_type: str) -> UUID:
        with self._lock:
            self.prune()
            if (
                len(self._items) >= 1000
                or sum(len(v.content) for v in self._items.values()) + len(content) > self.max_bytes
            ):
                raise RuntimeError("transient_capacity")
            identifier = uuid4()
            self._items[identifier] = Artifact(owner_id, content, mime_type, time.monotonic() + self.ttl_seconds)
            return identifier

    def get(self, identifier: UUID, owner_id: UUID) -> Artifact | None:
        with self._lock:
            self.prune()
            artifact = self._items.get(identifier)
            return artifact if artifact and artifact.owner_id == owner_id else None

    def discard(self, identifier: UUID) -> None:
        with self._lock:
            self._items.pop(identifier, None)

    def clear_owner(self, owner_id: UUID) -> None:
        with self._lock:
            self._items = {k: v for k, v in self._items.items() if v.owner_id != owner_id}
