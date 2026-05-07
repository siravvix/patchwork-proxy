"""Simple in-memory response cache with TTL and LRU eviction."""
from __future__ import annotations

import time
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class CacheConfig:
    ttl_seconds: float = 30.0
    max_entries: int = 256
    cacheable_methods: List[str] = field(default_factory=lambda: ["GET", "HEAD"])
    cacheable_statuses: List[int] = field(default_factory=lambda: [200, 203, 204, 301, 404])

    def __post_init__(self) -> None:
        if self.ttl_seconds <= 0:
            raise ValueError("ttl_seconds must be positive")
        if self.max_entries < 1:
            raise ValueError("max_entries must be at least 1")


@dataclass
class CachedResponse:
    status_code: int
    headers: Dict[str, str]
    body: bytes
    expires_at: float

    def is_expired(self) -> bool:
        return time.monotonic() >= self.expires_at


class ResponseCache:
    """Thread-unsafe LRU cache; suitable for single-threaded proxy workers."""

    def __init__(self, config: CacheConfig) -> None:
        self.config = config
        self._store: OrderedDict[str, CachedResponse] = OrderedDict()

    def get(self, key: str) -> Optional[CachedResponse]:
        entry = self._store.get(key)
        if entry is None:
            return None
        if entry.is_expired():
            del self._store[key]
            return None
        self._store.move_to_end(key)
        return entry

    def put(
        self,
        key: str,
        status_code: int,
        headers: Dict[str, str],
        body: bytes,
    ) -> None:
        expires_at = time.monotonic() + self.config.ttl_seconds
        self._store[key] = CachedResponse(
            status_code=status_code,
            headers=dict(headers),
            body=body,
            expires_at=expires_at,
        )
        self._store.move_to_end(key)
        while len(self._store) > self.config.max_entries:
            self._store.popitem(last=False)

    def invalidate(self, key: str) -> None:
        self._store.pop(key, None)

    def clear(self) -> None:
        self._store.clear()

    def size(self) -> int:
        return len(self._store)

    def stats(self) -> Dict[str, int]:
        total = len(self._store)
        expired = sum(1 for v in self._store.values() if v.is_expired())
        return {"total": total, "expired": expired, "live": total - expired}
