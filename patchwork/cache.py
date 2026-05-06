"""Simple in-memory response cache with TTL support for patchwork-proxy."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from threading import Lock
from typing import Dict, Optional, Tuple


@dataclass
class CacheConfig:
    ttl_seconds: float = 5.0
    max_entries: int = 256
    cacheable_methods: Tuple[str, ...] = ("GET", "HEAD")
    cacheable_statuses: Tuple[int, ...] = (200, 203, 204, 206, 300, 301, 404, 405)

    def __post_init__(self) -> None:
        if self.ttl_seconds <= 0:
            raise ValueError("ttl_seconds must be positive")
        if self.max_entries < 1:
            raise ValueError("max_entries must be at least 1")


@dataclass
class CachedResponse:
    status: int
    headers: Dict[str, str]
    body: bytes
    expires_at: float

    def is_expired(self) -> bool:
        return time.monotonic() >= self.expires_at


class ResponseCache:
    def __init__(self, config: CacheConfig) -> None:
        self._config = config
        self._store: Dict[str, CachedResponse] = {}
        self._lock = Lock()

    def _make_key(self, method: str, url: str) -> str:
        return f"{method.upper()}:{url}"

    def get(self, method: str, url: str) -> Optional[CachedResponse]:
        if method.upper() not in self._config.cacheable_methods:
            return None
        key = self._make_key(method, url)
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return None
            if entry.is_expired():
                del self._store[key]
                return None
            return entry

    def put(
        self,
        method: str,
        url: str,
        status: int,
        headers: Dict[str, str],
        body: bytes,
    ) -> bool:
        if method.upper() not in self._config.cacheable_methods:
            return False
        if status not in self._config.cacheable_statuses:
            return False
        key = self._make_key(method, url)
        expires_at = time.monotonic() + self._config.ttl_seconds
        entry = CachedResponse(status=status, headers=headers, body=body, expires_at=expires_at)
        with self._lock:
            if key not in self._store and len(self._store) >= self._config.max_entries:
                self._evict_one()
            self._store[key] = entry
        return True

    def _evict_one(self) -> None:
        """Remove the entry closest to expiry (cheapest eviction without LRU overhead)."""
        if not self._store:
            return
        oldest_key = min(self._store, key=lambda k: self._store[k].expires_at)
        del self._store[oldest_key]

    def invalidate(self, method: str, url: str) -> None:
        key = self._make_key(method, url)
        with self._lock:
            self._store.pop(key, None)

    def clear(self) -> None:
        with self._lock:
            self._store.clear()

    @property
    def size(self) -> int:
        with self._lock:
            return len(self._store)
