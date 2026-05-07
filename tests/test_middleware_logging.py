"""Tests for patchwork.middleware_logging."""

from __future__ import annotations

import time
from unittest.mock import patch

import pytest

from patchwork.middleware import MiddlewarePipeline, RequestContext
from patchwork.middleware_logging import (
    build_default_logging_middleware,
    make_logging_middleware,
)


def make_ctx(**kwargs) -> RequestContext:
    request = {"method": "GET", "path": "/api/test", "headers": {}, **kwargs}
    return RequestContext(request=request)


# ---------------------------------------------------------------------------
# make_logging_middleware
# ---------------------------------------------------------------------------

def test_pre_middleware_stamps_start_time():
    pre, _ = make_logging_middleware()
    ctx = make_ctx()
    assert "_log_start" not in ctx.state
    with patch("patchwork.middleware_logging.logger"):
        result = pre(ctx)
    assert "_log_start" in result.state
    assert isinstance(result.state["_log_start"], float)


def test_pre_middleware_logs_request_received(caplog):
    pre, _ = make_logging_middleware()
    ctx = make_ctx(target="http://localhost:8080")
    with patch("patchwork.middleware_logging.logger") as mock_log:
        pre(ctx)
    mock_log.info.assert_called_once()
    logged = mock_log.info.call_args[0][0]
    assert logged["event"] == "request_received"
    assert logged["route"] == "GET /api/test"


def test_pre_middleware_includes_headers_when_enabled():
    pre, _ = make_logging_middleware(log_request_headers=True)
    ctx = make_ctx(headers={"Authorization": "Bearer tok"})
    with patch("patchwork.middleware_logging.logger") as mock_log:
        pre(ctx)
    logged = mock_log.info.call_args[0][0]
    assert "request_headers" in logged
    assert logged["request_headers"]["Authorization"] == "Bearer tok"


def test_pre_middleware_omits_headers_by_default():
    pre, _ = make_logging_middleware()
    ctx = make_ctx(headers={"Authorization": "Bearer tok"})
    with patch("patchwork.middleware_logging.logger") as mock_log:
        pre(ctx)
    logged = mock_log.info.call_args[0][0]
    assert "request_headers" not in logged


def test_post_middleware_logs_request_completed():
    pre, post = make_logging_middleware()
    ctx = make_ctx()
    ctx.response = {"status": 200, "headers": {}, "body": "ok"}
    ctx.state["_log_start"] = time.monotonic() - 0.1
    with patch("patchwork.middleware_logging.logger") as mock_log:
        post(ctx)
    logged = mock_log.info.call_args[0][0]
    assert logged["event"] == "request_completed"
    assert logged["status"] == 200
    assert logged["elapsed_ms"] is not None and logged["elapsed_ms"] > 0


def test_post_middleware_handles_missing_start():
    _, post = make_logging_middleware()
    ctx = make_ctx()
    ctx.response = {"status": 502, "headers": {}, "body": ""}
    with patch("patchwork.middleware_logging.logger") as mock_log:
        post(ctx)
    logged = mock_log.info.call_args[0][0]
    assert logged["elapsed_ms"] is None


def test_post_middleware_includes_response_headers_when_enabled():
    _, post = make_logging_middleware(log_response_headers=True)
    ctx = make_ctx()
    ctx.response = {"status": 200, "headers": {"X-Custom": "yes"}, "body": ""}
    ctx.state["_log_start"] = time.monotonic()
    with patch("patchwork.middleware_logging.logger") as mock_log:
        post(ctx)
    logged = mock_log.info.call_args[0][0]
    assert "response_headers" in logged


def test_post_middleware_includes_body_when_enabled():
    _, post = make_logging_middleware(log_body=True)
    ctx = make_ctx()
    ctx.response = {"status": 200, "headers": {}, "body": "hello"}
    ctx.state["_log_start"] = time.monotonic()
    with patch("patchwork.middleware_logging.logger") as mock_log:
        post(ctx)
    logged = mock_log.info.call_args[0][0]
    assert logged["response_body"] == "hello"


# ---------------------------------------------------------------------------
# build_default_logging_middleware
# ---------------------------------------------------------------------------

def test_build_default_registers_both_hooks():
    pipeline = MiddlewarePipeline()
    build_default_logging_middleware(pipeline)
    assert len(pipeline._pre) == 1
    assert len(pipeline._post) == 1
