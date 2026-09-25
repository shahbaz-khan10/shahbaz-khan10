"""Rate limiting for the login endpoint (Redis-backed with an in-process fallback)."""

import time
from collections import defaultdict, deque
from threading import Lock

from django.conf import settings

try:
    import redis as redis_lib
except ImportError:  # pragma: no cover
    redis_lib = None


class _InMemoryLimiter:
    def __init__(self):
        self._store = defaultdict(deque)
        self._lock = Lock()

    def hit(self, key, limit, window_seconds):
        now = time.time()
        with self._lock:
            bucket = self._store[key]
            while bucket and bucket[0] < now - window_seconds:
                bucket.popleft()
            bucket.append(now)
            count = len(bucket)
            return count <= limit, max(0, limit - count), max(0, round(bucket[0] + window_seconds - now))

    def clear(self):
        with self._lock:
            self._store.clear()


class RateLimiter:
    """Sliding-window limiter. `hit(key, limit, window)` -> (allowed, remaining, retry_after)."""

    def __init__(self):
        self._redis = None
        if settings.REDIS_URL and redis_lib is not None:
            try:
                self._redis = redis_lib.Redis.from_url(settings.REDIS_URL, socket_connect_timeout=1)
                self._redis.ping()
            except Exception:
                self._redis = None
        self._mem = _InMemoryLimiter()

    def hit(self, key, limit=None, window_seconds=None):
        limit = limit or settings.LOGIN_RATE_LIMIT_ATTEMPTS
        window_seconds = window_seconds or settings.LOGIN_RATE_LIMIT_WINDOW_SECONDS
        redis_key = f"ratelimit:{key}:{int(time.time() // window_seconds)}"

        if self._redis is not None:
            try:
                count = self._redis.incr(redis_key)
                if count == 1:
                    self._redis.expire(redis_key, window_seconds + 5)
                allowed = count <= limit
                remaining = max(0, limit - count)
                retry_after = 0 if allowed else int(round((count - limit) * 1e-3) or 1)
                return allowed, remaining, retry_after
            except Exception:
                pass
        return self._mem.hit(key, limit, window_seconds)

    def clear(self):
        if self._redis is not None:
            try:
                self._redis.flushdb()
            except Exception:
                pass
        self._mem.clear()


limiter = RateLimiter()


def login_key(ip_address) -> str:
    return f"login:{ip_address or 'unknown'}"