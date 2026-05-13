"""Tests for patchwork.middleware_request_id_log."""
import pytest

from patchwork.middleware import RequestContext
from patchwork.middleware_request_id_log import (
    RequestIdLogConfig,
    make_request_id_log_middleware,
    build_default_request_id_log_middleware,
)


def make_ctx(**kwargs) -> RequestContext:
    ctx = RequestContext(
        method=kwargs.get("method", "GET"),
        path=kwargs.get("path", "/test"),
        headers=kwargs.get("headers", {}),
        query=kwargs.get("query", {}),
        body=kwargs.get("body", b""),
    )
    ctx.metadata.update(kwargs.get("metadata", {}))
    ctx.response = kwargs.get("response", None)
    return ctx


# --- Config tests ---

def test_config_defaults():
    cfg = RequestIdLogConfig()
    assert cfg.enabled is True
    assert cfg.header_name == "X-Request-ID"
    assert cfg.log_on_request is True
    assert cfg.log_on_response is True


def test_config_empty_header_raises():
    with pytest.raises(ValueError, match="header_name"):
        RequestIdLogConfig(header_name="")


def test_config_from_dict_full():
    cfg = RequestIdLogConfig.from_dict({
        "enabled": False,
        "header_name": "X-Trace-ID",
        "log_on_request": False,
        "log_on_response": False,
    })
    assert cfg.enabled is False
    assert cfg.header_name == "X-Trace-ID"
    assert cfg.log_on_request is False
    assert cfg.log_on_response is False


def test_config_from_dict_defaults():
    cfg = RequestIdLogConfig.from_dict({})
    assert cfg.enabled is True
    assert cfg.header_name == "X-Request-ID"


# --- Middleware behaviour tests ---

def test_pre_middleware_logs_when_request_id_present(caplog):
    cfg = RequestIdLogConfig()
    pre, _ = make_request_id_log_middleware(cfg)
    ctx = make_ctx(metadata={"request_id": "abc-123"})
    with caplog.at_level("INFO"):
        pre(ctx)
    assert any("request received" in r.message for r in caplog.records)


def test_pre_middleware_silent_without_request_id(caplog):
    cfg = RequestIdLogConfig()
    pre, _ = make_request_id_log_middleware(cfg)
    ctx = make_ctx()
    with caplog.at_level("INFO"):
        pre(ctx)
    assert not any("request received" in r.message for r in caplog.records)


def test_post_middleware_logs_response(caplog):
    cfg = RequestIdLogConfig()
    _, post = make_request_id_log_middleware(cfg)
    ctx = make_ctx(metadata={"request_id": "xyz-789"}, response={"status": 200})
    with caplog.at_level("INFO"):
        post(ctx)
    assert any("response sent" in r.message for r in caplog.records)


def test_disabled_middleware_does_not_log(caplog):
    cfg = RequestIdLogConfig(enabled=False)
    pre, post = make_request_id_log_middleware(cfg)
    ctx = make_ctx(metadata={"request_id": "abc-123"}, response={"status": 200})
    with caplog.at_level("INFO"):
        pre(ctx)
        post(ctx)
    assert not caplog.records


def test_log_on_request_false_skips_pre(caplog):
    cfg = RequestIdLogConfig(log_on_request=False)
    pre, _ = make_request_id_log_middleware(cfg)
    ctx = make_ctx(metadata={"request_id": "abc-123"})
    with caplog.at_level("INFO"):
        pre(ctx)
    assert not any("request received" in r.message for r in caplog.records)


def test_build_default_returns_callables():
    pre, post = build_default_request_id_log_middleware()
    assert callable(pre)
    assert callable(post)
