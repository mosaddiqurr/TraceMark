"""Bounded limiter for the documented single API worker deployment."""

from __future__ import annotations

import hashlib
import hmac
import threading
import time


class RateLimiter:
    def __init__(self, pepper: str):
        self._pepper = pepper.encode()
        self._buckets: dict[str, tuple[int, float]] = {}
        self._lock = threading.Lock()

    def allow(self, identity: str, category: str, limit: int, window_seconds: int) -> bool:
        key = hmac.new(self._pepper, f"{identity}:{category}".encode(), hashlib.sha256).hexdigest()
        now = time.monotonic()
        with self._lock:
            self._buckets = {k: v for k, v in self._buckets.items() if v[1] > now}
            count, until = self._buckets.get(key, (0, now + window_seconds))
            if key not in self._buckets and len(self._buckets) >= 4096:
                return False
            self._buckets[key] = (count + 1, until)
            return count < limit
