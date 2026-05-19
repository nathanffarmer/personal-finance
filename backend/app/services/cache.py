from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable, Callable
from typing import Any, TypeVar

T = TypeVar("T")


class TTLCache:
    """Tiny async-friendly TTL cache.

    Used to avoid re-hitting Monarch on every page load. Not thread-safe
    across processes; fine for a single uvicorn worker.
    """

    def __init__(self) -> None:
        self._store: dict[str, tuple[float, Any]] = {}
        self._lock = asyncio.Lock()

    async def get_or_set(
        self,
        key: str,
        ttl_seconds: int,
        loader: Callable[[], Awaitable[T]],
    ) -> T:
        now = time.monotonic()
        hit = self._store.get(key)
        if hit and hit[0] > now:
            return hit[1]
        async with self._lock:
            hit = self._store.get(key)
            if hit and hit[0] > now:
                return hit[1]
            value = await loader()
            self._store[key] = (now + ttl_seconds, value)
            return value

    def clear(self, prefix: str | None = None) -> int:
        if prefix is None:
            n = len(self._store)
            self._store.clear()
            return n
        keys = [k for k in self._store if k.startswith(prefix)]
        for k in keys:
            del self._store[k]
        return len(keys)


_cache = TTLCache()


def get_cache() -> TTLCache:
    return _cache
