"""Unit tests for middleware_retry.py."""
import pytest
from patchwork.middleware import RequestContext
from patchwork.retry import RetryConfig
from patchwork.middleware_retry import (
    make_retry_middleware,
    build_default_retry_middleware,
    _RETRY_CONFIG_KEY,
    _RETRY_ATTEMPTS_KEY,
    _RETRY_EXHAUSTED_KEY,
)


def make_ctx(status=None, attempts=0):
    ctx = RequestContext(
        request={"method": "GET", "path": "/api"},
        response={"status": status} if status else None,
    )
    ctx.meta[_RETRY_ATTEMPTS_KEY] = attempts
    return ctx


@pytest.fixture
def config():
    return RetryConfig(
        max_attempts=3,
        retryable_statuses={502, 503, 504},
        backoff_base=0.5,
        backoff_max=10.0,
    )


def test_pre_middleware_attaches_config(config):
    pre, _ = make_retry_middleware(config)
    ctx = make_ctx()
    pre(ctx)
    assert ctx.meta[_RETRY_CONFIG_KEY] is config


def test_pre_middleware_initialises_attempts(config):
    pre, _ = make_retry_middleware(config)
    ctx = RequestContext(request={"method": "GET", "path": "/"}, response=None)
    pre(ctx)
    assert ctx.meta[_RETRY_ATTEMPTS_KEY] == 0


def test_post_middleware_non_retryable_status(config):
    _, post = make_retry_middleware(config)
    ctx = make_ctx(status=200, attempts=0)
    post(ctx)
    assert ctx.meta["should_retry"] is False
    assert _RETRY_EXHAUSTED_KEY not in ctx.meta


def test_post_middleware_retryable_status_first_attempt(config):
    _, post = make_retry_middleware(config)
    ctx = make_ctx(status=503, attempts=0)
    post(ctx)
    assert ctx.meta["should_retry"] is True
    assert ctx.meta["retry_delay"] == config.backoff_seconds(0)


def test_post_middleware_retryable_status_exhausted(config):
    _, post = make_retry_middleware(config)
    # attempts already at max_attempts - 1 so next would exceed
    ctx = make_ctx(status=502, attempts=2)
    post(ctx)
    assert ctx.meta["should_retry"] is False
    assert ctx.meta[_RETRY_EXHAUSTED_KEY] is True


def test_post_middleware_increments_attempts(config):
    _, post = make_retry_middleware(config)
    ctx = make_ctx(status=200, attempts=1)
    post(ctx)
    assert ctx.meta[_RETRY_ATTEMPTS_KEY] == 2


def test_post_middleware_no_response(config):
    _, post = make_retry_middleware(config)
    ctx = make_ctx(status=None, attempts=0)
    post(ctx)
    assert ctx.meta["should_retry"] is False


def test_build_default_retry_middleware_defaults():
    rc = build_default_retry_middleware()
    assert rc.max_attempts == 3
    assert 503 in rc.retryable_statuses


def test_build_default_retry_middleware_overrides():
    rc = build_default_retry_middleware({"max_attempts": 5, "backoff_base": 1.0})
    assert rc.max_attempts == 5
    assert rc.backoff_base == 1.0
