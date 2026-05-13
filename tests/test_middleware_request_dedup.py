"""Tests for request deduplication middleware."""
import threading
from typing import Dict

import pytest

from patchwork.middleware import RequestContext
from patchwork.middleware_request_dedup import (
    RequestDedupConfig,
    _request_key,
    make_request_dedup_middleware,
)


def make_ctx(**kwargs) -> RequestContext:
    ctx = RequestContext()
    ctx.target = kwargs.get("target", "/api/test")
    ctx.request_headers = kwargs.get("request_headers", {"method": "GET"})
    ctx.request_body = kwargs.get("request_body", b"")
    ctx.response_headers = {}
    ctx.metadata = {}
    return ctx


def test_config_defaults():
    cfg = RequestDedupConfig()
    assert cfg.enabled is False
    assert cfg.include_body is True
    assert cfg.include_query is True
    assert cfg.reject_status == 429
    assert cfg.reason_header == "X-Dedup-Reason"


def test_config_invalid_reject_status_raises():
    with pytest.raises(ValueError, match="reject_status"):
        RequestDedupConfig(enabled=True, reject_status=200)


def test_config_empty_reason_header_raises():
    with pytest.raises(ValueError, match="reason_header"):
        RequestDedupConfig(enabled=True, reason_header="  ")


def test_config_from_dict():
    cfg = RequestDedupConfig.from_dict({"enabled": True, "reject_status": 503, "include_body": False})
    assert cfg.enabled is True
    assert cfg.reject_status == 503
    assert cfg.include_body is False


def test_disabled_middleware_passes_through():
    cfg = RequestDedupConfig(enabled=False)
    pre, post = make_request_dedup_middleware(cfg)
    ctx = make_ctx()
    result = pre(ctx)
    assert not hasattr(result, "skip_upstream") or not result.skip_upstream


def test_first_request_registers_key():
    cfg = RequestDedupConfig(enabled=True)
    registry: Dict[str, bool] = {}
    pre, post = make_request_dedup_middleware(cfg, registry=registry)
    ctx = make_ctx()
    pre(ctx)
    assert len(registry) == 1


def test_duplicate_request_is_rejected():
    cfg = RequestDedupConfig(enabled=True)
    registry: Dict[str, bool] = {}
    pre, _ = make_request_dedup_middleware(cfg, registry=registry)
    ctx1 = make_ctx()
    pre(ctx1)
    ctx2 = make_ctx()
    result = pre(ctx2)
    assert result.response_status == 429
    assert result.response_headers.get("X-Dedup-Reason") == "duplicate-in-flight"
    assert getattr(result, "skip_upstream", False) is True


def test_post_middleware_clears_key():
    cfg = RequestDedupConfig(enabled=True)
    registry: Dict[str, bool] = {}
    pre, post = make_request_dedup_middleware(cfg, registry=registry)
    ctx = make_ctx()
    pre(ctx)
    assert len(registry) == 1
    post(ctx)
    assert len(registry) == 0


def test_second_request_allowed_after_first_completes():
    cfg = RequestDedupConfig(enabled=True)
    registry: Dict[str, bool] = {}
    pre, post = make_request_dedup_middleware(cfg, registry=registry)
    ctx1 = make_ctx()
    pre(ctx1)
    post(ctx1)
    ctx2 = make_ctx()
    result = pre(ctx2)
    assert result.response_status != 429


def test_different_paths_not_deduped():
    cfg = RequestDedupConfig(enabled=True)
    registry: Dict[str, bool] = {}
    pre, _ = make_request_dedup_middleware(cfg, registry=registry)
    ctx1 = make_ctx(target="/a")
    ctx2 = make_ctx(target="/b")
    pre(ctx1)
    result = pre(ctx2)
    assert getattr(result, "skip_upstream", False) is not True


def test_request_key_includes_body_hash():
    cfg = RequestDedupConfig(enabled=True, include_body=True)
    ctx_a = make_ctx(request_body=b"hello")
    ctx_b = make_ctx(request_body=b"world")
    assert _request_key(ctx_a, cfg) != _request_key(ctx_b, cfg)


def test_request_key_excludes_body_when_disabled():
    cfg = RequestDedupConfig(enabled=True, include_body=False)
    ctx_a = make_ctx(request_body=b"hello")
    ctx_b = make_ctx(request_body=b"world")
    assert _request_key(ctx_a, cfg) == _request_key(ctx_b, cfg)
