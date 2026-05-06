"""Tests for the token-bucket rate limiter."""

import time
import pytest
from patchwork.rate_limiter import RateLimitConfig, TokenBucket, RateLimiter


# --- RateLimitConfig ---

def test_rate_limit_config_defaults():
    cfg = RateLimitConfig()
    assert cfg.requests_per_second == 10.0
    assert cfg.burst == 20


def test_rate_limit_config_invalid_rps():
    with pytest.raises(ValueError, match="requests_per_second"):
        RateLimitConfig(requests_per_second=0)


def test_rate_limit_config_invalid_burst():
    with pytest.raises(ValueError, match="burst"):
        RateLimitConfig(burst=0)


# --- TokenBucket ---

def test_token_bucket_allows_up_to_burst():
    cfg = RateLimitConfig(requests_per_second=1.0, burst=5)
    bucket = TokenBucket(cfg)
    results = [bucket.acquire() for _ in range(5)]
    assert all(results)


def test_token_bucket_throttles_beyond_burst():
    cfg = RateLimitConfig(requests_per_second=1.0, burst=3)
    bucket = TokenBucket(cfg)
    for _ in range(3):
        bucket.acquire()
    assert bucket.acquire() is False


def test_token_bucket_refills_over_time():
    cfg = RateLimitConfig(requests_per_second=100.0, burst=1)
    bucket = TokenBucket(cfg)
    assert bucket.acquire() is True
    assert bucket.acquire() is False
    time.sleep(0.05)  # 100 rps -> ~5 tokens in 50ms
    assert bucket.acquire() is True


def test_token_bucket_available_tokens_does_not_exceed_burst():
    cfg = RateLimitConfig(requests_per_second=1000.0, burst=10)
    bucket = TokenBucket(cfg)
    time.sleep(0.05)
    assert bucket.available_tokens <= 10.0


# --- RateLimiter ---

def test_rate_limiter_allows_requests_within_limit():
    limiter = RateLimiter(RateLimitConfig(requests_per_second=100.0, burst=10))
    for _ in range(10):
        assert limiter.is_allowed("route-a") is True


def test_rate_limiter_throttles_after_burst():
    limiter = RateLimiter(RateLimitConfig(requests_per_second=1.0, burst=2))
    limiter.is_allowed("route-b")
    limiter.is_allowed("route-b")
    assert limiter.is_allowed("route-b") is False


def test_rate_limiter_routes_are_independent():
    limiter = RateLimiter(RateLimitConfig(requests_per_second=1.0, burst=1))
    assert limiter.is_allowed("route-x") is True
    assert limiter.is_allowed("route-y") is True  # separate bucket


def test_rate_limiter_per_route_config():
    limiter = RateLimiter(RateLimitConfig(requests_per_second=1.0, burst=1))
    limiter.configure_route("vip", RateLimitConfig(requests_per_second=100.0, burst=50))
    for _ in range(50):
        assert limiter.is_allowed("vip") is True


def test_rate_limiter_reset_restores_bucket():
    limiter = RateLimiter(RateLimitConfig(requests_per_second=1.0, burst=1))
    limiter.is_allowed("route-r")
    assert limiter.is_allowed("route-r") is False
    limiter.reset("route-r")
    assert limiter.is_allowed("route-r") is True
