"""Small Redis-backed fixed-window limiter for abuse-sensitive endpoints."""

from __future__ import annotations

import time


class RateLimiter:
    def __init__(self, redis_client: object | None = None):
        self.redis = redis_client
        self.memory: dict[str, tuple[int, int]] = {}

    async def allow(self, key: str, limit: int, window_seconds: int) -> bool:
        window = int(time.time()) // window_seconds
        namespaced = f"rate:{window}:{key}"
        if self.redis is not None:
            count = await self.redis.incr(namespaced)  # type: ignore[attr-defined]
            if count == 1:
                await self.redis.expire(namespaced, window_seconds + 1)  # type: ignore[attr-defined]
            return int(count) <= limit
        count, stored_window = self.memory.get(key, (0, window))
        if stored_window != window:
            count = 0
        count += 1
        self.memory[key] = (count, window)
        return count <= limit

