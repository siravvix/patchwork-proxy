"""Tests for patchwork.middleware_timeout."""

import time
from unittest.mock import patch

import pytest

from patchwork.middleware import RequestContext
from patchwork.timeout import TimeoutConfig
from patchwork.middleware_timeout import (
    make_timeout_middleware,
    is_timed_out,
    build_default_timeout_middleware,
)


def make_ctx(method="GET", path="/") -> RequestContext:
    return RequestContext(method=method, path=path, headers={}, body=b"")


def test_middleware_attaches_timeout_config():
    cfg = TimeoutConfig(connect_seconds=1.0, read_seconds=5.0)
    mw = make_timeout_middleware(cfg)
    ctx = make_ctx()
    result = mw(ctx)
    assert result.extra["timeout_config"] is cfg
    assert result.extra["timeout_connect"] == 1.0
    assert result.extra["timeout_read"] == 5.0


def test_middleware_sets_start_time():
    mw = make_timeout_middleware()
    ctx = make_ctx()
    assert not hasattr(ctx, "_timeout_start")
    mw(ctx)
    assert hasattr(ctx, "_timeout_start")


def test_middleware_does_not_overwrite_existing_start():
    mw = make_timeout_middleware()
    ctx = make_ctx()
    ctx._timeout_start = 12345.0  # type: ignore[attr-defined]
    mw(ctx)
    assert ctx._timeout_start == 12345.0  # type: ignore[attr-defined]


def test_is_timed_out_no_config():
    ctx = make_ctx()
    assert is_timed_out(ctx) is False


def test_is_timed_out_no_total():
    cfg = TimeoutConfig()  # no total_seconds
    mw = make_timeout_middleware(cfg)
    ctx = make_ctx()
    mw(ctx)
    assert is_timed_out(ctx) is False


def test_is_timed_out_within_limit():
    cfg = TimeoutConfig(total_seconds=60.0)
    mw = make_timeout_middleware(cfg)
    ctx = make_ctx()
    mw(ctx)
    assert is_timed_out(ctx) is False


def test_is_timed_out_exceeded():
    cfg = TimeoutConfig(total_seconds=0.01)
    mw = make_timeout_middleware(cfg)
    ctx = make_ctx()
    mw(ctx)
    time.sleep(0.02)
    assert is_timed_out(ctx) is True


def test_build_default_returns_callable():
    mw = build_default_timeout_middleware()
    ctx = make_ctx()
    result = mw(ctx)
    assert "timeout_config" in result.extra
