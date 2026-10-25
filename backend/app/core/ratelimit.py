"""Fixed-window rate limiter: Redis when configured, in-memory otherwise (dev/tests)."""

import threading
import time
from typing import Protocol

from app.core.config import get_settings


class Limiter(Protocol):
    def hit(self, key: str, limit: int, window_seconds: int) -> bool:
        """Record a hit; return False if the limit is exceeded."""
        ...

    def reset(self) -> None: ...


class MemoryLimiter:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._buckets: dict[str, tuple[float, int]] = {}

    def hit(self, key: str, limit: int, window_seconds: int) -> bool:
        now = time.monotonic()
        with self._lock:
            start, count = self._buckets.get(key, (now, 0))
            if now - start >= window_seconds:
                start, count = now, 0
            count += 1
            self._buckets[key] = (start, count)
            return count <= limit

    def reset(self) -> None:
        with self._lock:
            self._buckets.clear()


class RedisLimiter:
    def __init__(self, url: str) -> None:
        import redis

        self._r = redis.Redis.from_url(url)

    def hit(self, key: str, limit: int, window_seconds: int) -> bool:
        k = f"rl:{key}"
        pipe = self._r.pipeline()
        pipe.incr(k)
        pipe.expire(k, window_seconds, nx=True)
        count, _ = pipe.execute()
        return int(count) <= limit

    def reset(self) -> None:
        for k in self._r.scan_iter("rl:*"):
            self._r.delete(k)


_limiter: Limiter | None = None


def get_limiter() -> Limiter:
    global _limiter
    if _limiter is None:
        url = get_settings().redis_url
        _limiter = RedisLimiter(url) if url else MemoryLimiter()
    return _limiter
