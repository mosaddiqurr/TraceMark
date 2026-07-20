from __future__ import annotations

import os

import dramatiq
from dramatiq.brokers.redis import RedisBroker

broker = RedisBroker(  # type: ignore[no-untyped-call]
    url=os.getenv("TRACEMARK_REDIS_URL", "redis://redis:6379/0"))
dramatiq.set_broker(broker)

