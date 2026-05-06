"""Tests for patchwork.cache."""

import time

import pytest

from patchwork.cache import CacheConfig, ResponseCache


@pytest.fixture()
def config() -> CacheConfig:
    return CacheConfig(ttl_seconds=1.0, max_entries=4)


@pytest.fixture()
def cache(config: CacheConfig) -> ResponseCache:
    return ResponseCache(config)


_HEADERS = {"content-type": "application/json"}
_BODY = b'{"ok": true}'


def test_cache_config_invalid_ttl() -> None:
    with pytest.raises(ValueError, match="ttl_seconds"):
        CacheConfig(ttl_seconds=0)


def test_cache_config_invalid_max_entries() -> None:
    with pytest.raises(ValueError, match="max_entries"):
        CacheConfig(max_entries=0)


def test_get_miss_returns_none(cache: ResponseCache) -> None:
    assert cache.get("GET", "http://example.com/api") is None


def test_put_and_get_hit(cache: ResponseCache) -> None:
    cache.put("GET", "http://example.com/api", 200, _HEADERS, _BODY)
    entry = cache.get("GET", "http://example.com/api")
    assert entry is not None
    assert entry.status == 200
    assert entry.body == _BODY
    assert entry.headers == _HEADERS


def test_non_cacheable_method_not_stored(cache: ResponseCache) -> None:
    stored = cache.put("POST", "http://example.com/api", 200, _HEADERS, _BODY)
    assert stored is False
    assert cache.get("POST", "http://example.com/api") is None


def test_non_cacheable_status_not_stored(cache: ResponseCache) -> None:
    stored = cache.put("GET", "http://example.com/api", 500, _HEADERS, _BODY)
    assert stored is False
    assert cache.get("GET", "http://example.com/api") is None


def test_expired_entry_returns_none(cache: ResponseCache) -> None:
    short_cache = ResponseCache(CacheConfig(ttl_seconds=0.05))
    short_cache.put("GET", "http://example.com/", 200, _HEADERS, _BODY)
    time.sleep(0.1)
    assert short_cache.get("GET", "http://example.com/") is None


def test_invalidate_removes_entry(cache: ResponseCache) -> None:
    cache.put("GET", "http://example.com/api", 200, _HEADERS, _BODY)
    cache.invalidate("GET", "http://example.com/api")
    assert cache.get("GET", "http://example.com/api") is None


def test_clear_empties_cache(cache: ResponseCache) -> None:
    cache.put("GET", "http://example.com/a", 200, _HEADERS, _BODY)
    cache.put("GET", "http://example.com/b", 200, _HEADERS, _BODY)
    cache.clear()
    assert cache.size == 0


def test_max_entries_evicts_on_overflow(config: CacheConfig) -> None:
    cache = ResponseCache(CacheConfig(ttl_seconds=60, max_entries=3))
    for i in range(4):
        cache.put("GET", f"http://example.com/{i}", 200, _HEADERS, _BODY)
    assert cache.size == 3


def test_size_reflects_stored_entries(cache: ResponseCache) -> None:
    assert cache.size == 0
    cache.put("GET", "http://example.com/x", 200, _HEADERS, _BODY)
    assert cache.size == 1
