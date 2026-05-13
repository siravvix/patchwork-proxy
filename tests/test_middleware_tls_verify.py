"""Unit tests for patchwork.middleware_tls_verify."""
import pytest

from patchwork.middleware import RequestContext
from patchwork.middleware_tls_verify import (
    TLSVerifyConfig,
    _is_secure,
    make_tls_verify_middleware,
)


def make_ctx(
    scheme: str = "",
    forwarded_proto: str = "",
    header_name: str = "X-Forwarded-Proto",
) -> RequestContext:
    ctx = RequestContext()
    ctx.request = {"scheme": scheme}
    ctx.request_headers = {header_name: forwarded_proto} if forwarded_proto else {}
    ctx.response_headers = {}
    return ctx


# ── TLSVerifyConfig ──────────────────────────────────────────────────────────

def test_config_defaults():
    cfg = TLSVerifyConfig()
    assert cfg.enabled is False
    assert cfg.forwarded_proto_header == "X-Forwarded-Proto"
    assert cfg.reject_status == 403


def test_config_empty_header_raises():
    with pytest.raises(ValueError, match="forwarded_proto_header"):
        TLSVerifyConfig(forwarded_proto_header="   ")


def test_config_invalid_reject_status_raises():
    with pytest.raises(ValueError, match="reject_status"):
        TLSVerifyConfig(reject_status=200)


def test_config_from_dict():
    cfg = TLSVerifyConfig.from_dict(
        {"enabled": True, "reject_status": 426, "reject_reason": "TLS only"}
    )
    assert cfg.enabled is True
    assert cfg.reject_status == 426
    assert cfg.reject_reason == "TLS only"


# ── _is_secure ───────────────────────────────────────────────────────────────

def test_is_secure_via_scheme():
    ctx = make_ctx(scheme="https")
    assert _is_secure(ctx, "X-Forwarded-Proto") is True


def test_is_secure_via_header():
    ctx = make_ctx(forwarded_proto="https")
    assert _is_secure(ctx, "X-Forwarded-Proto") is True


def test_is_not_secure_http():
    ctx = make_ctx(scheme="http")
    assert _is_secure(ctx, "X-Forwarded-Proto") is False


def test_is_not_secure_empty():
    ctx = make_ctx()
    assert _is_secure(ctx, "X-Forwarded-Proto") is False


# ── middleware ────────────────────────────────────────────────────────────────

def test_middleware_disabled_passes_http():
    cfg = TLSVerifyConfig(enabled=False)
    mw = make_tls_verify_middleware(cfg)
    ctx = make_ctx(scheme="http")
    result = mw(ctx)
    assert result is ctx
    assert not getattr(ctx, "short_circuit", False)


def test_middleware_enabled_passes_https_scheme():
    cfg = TLSVerifyConfig(enabled=True)
    mw = make_tls_verify_middleware(cfg)
    ctx = make_ctx(scheme="https")
    result = mw(ctx)
    assert result is ctx
    assert not getattr(ctx, "short_circuit", False)


def test_middleware_enabled_passes_https_header():
    cfg = TLSVerifyConfig(enabled=True)
    mw = make_tls_verify_middleware(cfg)
    ctx = make_ctx(forwarded_proto="https")
    result = mw(ctx)
    assert not getattr(ctx, "short_circuit", False)


def test_middleware_enabled_blocks_http():
    cfg = TLSVerifyConfig(enabled=True, reject_status=403)
    mw = make_tls_verify_middleware(cfg)
    ctx = make_ctx(scheme="http")
    result = mw(ctx)
    assert result.short_circuit is True
    assert result.response_status == 403
    assert result.response_headers.get("X-TLS-Verify") == "rejected"


def test_middleware_custom_reject_status():
    cfg = TLSVerifyConfig(enabled=True, reject_status=426, reject_reason="Upgrade")
    mw = make_tls_verify_middleware(cfg)
    ctx = make_ctx(scheme="http")
    result = mw(ctx)
    assert result.response_status == 426
    assert result.response_body == b"Upgrade"
