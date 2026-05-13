"""Tests for patchwork.middleware_query_filter."""
import pytest

from patchwork.middleware import RequestContext
from patchwork.middleware_query_filter import (
    QueryFilterConfig,
    _parse_query_keys,
    build_default_query_filter_middleware,
    make_query_filter_middleware,
)


def make_ctx(url: str = "http://localhost/api", method: str = "GET") -> RequestContext:
    ctx = RequestContext()
    ctx.request = {"url": url, "method": method, "headers": {}}
    return ctx


# --- QueryFilterConfig ---

def test_config_defaults():
    cfg = QueryFilterConfig()
    assert cfg.enabled is False
    assert cfg.blocked_params == []
    assert cfg.required_params == []
    assert cfg.reject_status == 400
    assert cfg.reason_header == "X-Query-Filter-Reason"


def test_config_invalid_reject_status_raises():
    with pytest.raises(ValueError, match="reject_status"):
        QueryFilterConfig(enabled=True, reject_status=200)


def test_config_empty_reason_header_raises():
    with pytest.raises(ValueError, match="reason_header"):
        QueryFilterConfig(enabled=True, reason_header="")


def test_config_from_dict():
    cfg = QueryFilterConfig.from_dict({
        "enabled": True,
        "blocked_params": ["debug"],
        "required_params": ["api_version"],
        "reject_status": 403,
        "reason_header": "X-Blocked",
    })
    assert cfg.enabled is True
    assert cfg.blocked_params == ["debug"]
    assert cfg.required_params == ["api_version"]
    assert cfg.reject_status == 403
    assert cfg.reason_header == "X-Blocked"


# --- _parse_query_keys ---

def test_parse_query_keys_extracts_keys():
    keys = _parse_query_keys("http://example.com/path?foo=1&bar=2")
    assert keys == {"foo", "bar"}


def test_parse_query_keys_empty_for_no_query():
    keys = _parse_query_keys("http://example.com/path")
    assert keys == set()


# --- middleware disabled ---

def test_middleware_disabled_passes_all():
    cfg = QueryFilterConfig(enabled=False, blocked_params=["debug"])
    mw = make_query_filter_middleware(cfg)
    ctx = make_ctx("http://localhost/api?debug=true")
    result = mw(ctx)
    assert result is ctx
    assert result.response is None


# --- blocked params ---

def test_middleware_blocks_forbidden_param():
    cfg = QueryFilterConfig(enabled=True, blocked_params=["debug"])
    mw = make_query_filter_middleware(cfg)
    ctx = make_ctx("http://localhost/api?debug=true")
    result = mw(ctx)
    assert result.response["status"] == 400
    assert "debug" in result.response["headers"]["X-Query-Filter-Reason"]


def test_middleware_allows_request_without_blocked_param():
    cfg = QueryFilterConfig(enabled=True, blocked_params=["debug"])
    mw = make_query_filter_middleware(cfg)
    ctx = make_ctx("http://localhost/api?page=1")
    result = mw(ctx)
    assert result.response is None


# --- required params ---

def test_middleware_blocks_missing_required_param():
    cfg = QueryFilterConfig(enabled=True, required_params=["api_version"])
    mw = make_query_filter_middleware(cfg)
    ctx = make_ctx("http://localhost/api?page=1")
    result = mw(ctx)
    assert result.response["status"] == 400
    assert "api_version" in result.response["headers"]["X-Query-Filter-Reason"]


def test_middleware_passes_when_required_param_present():
    cfg = QueryFilterConfig(enabled=True, required_params=["api_version"])
    mw = make_query_filter_middleware(cfg)
    ctx = make_ctx("http://localhost/api?api_version=2")
    result = mw(ctx)
    assert result.response is None


# --- custom reject status ---

def test_middleware_uses_custom_reject_status():
    cfg = QueryFilterConfig(enabled=True, blocked_params=["secret"], reject_status=403)
    mw = make_query_filter_middleware(cfg)
    ctx = make_ctx("http://localhost/api?secret=xyz")
    result = mw(ctx)
    assert result.response["status"] == 403


# --- build_default ---

def test_build_default_returns_disabled_middleware():
    mw = build_default_query_filter_middleware()
    ctx = make_ctx("http://localhost/api?debug=1")
    result = mw(ctx)
    assert result.response is None
