"""Unit tests for the request signing middleware."""
import hashlib
import hmac
import time

import pytest

from patchwork.middleware import RequestContext
from patchwork.middleware_request_signing import (
    RequestSigningConfig,
    _compute_signature,
    make_request_signing_middleware,
)


def make_ctx(**kwargs) -> RequestContext:
    ctx = RequestContext()
    ctx.method = kwargs.get("method", "GET")
    ctx.path = kwargs.get("path", "/api/data")
    ctx.request_headers = kwargs.get("request_headers", {})
    return ctx


def _sign(secret, method, path, ts, extra=None):
    return _compute_signature(secret, method, path, str(ts), extra or {})


# --- Config tests ---

def test_config_defaults():
    cfg = RequestSigningConfig()
    assert cfg.enabled is False
    assert cfg.header_name == "X-Signature"
    assert cfg.max_skew_seconds == 30
    assert cfg.reject_status == 401


def test_config_enabled_requires_secret():
    with pytest.raises(ValueError, match="secret"):
        RequestSigningConfig(enabled=True, secret="")


def test_config_empty_header_raises():
    with pytest.raises(ValueError, match="header_name"):
        RequestSigningConfig(header_name="")


def test_config_negative_skew_raises():
    with pytest.raises(ValueError, match="max_skew_seconds"):
        RequestSigningConfig(max_skew_seconds=-1)


def test_config_invalid_reject_status_raises():
    with pytest.raises(ValueError, match="reject_status"):
        RequestSigningConfig(reject_status=200)


def test_config_from_dict():
    cfg = RequestSigningConfig.from_dict({
        "enabled": True, "secret": "mysecret", "max_skew_seconds": 60
    })
    assert cfg.enabled is True
    assert cfg.secret == "mysecret"
    assert cfg.max_skew_seconds == 60


# --- Middleware tests ---

def test_disabled_passes_all():
    cfg = RequestSigningConfig(enabled=False)
    mw = make_request_signing_middleware(cfg)
    ctx = make_ctx()
    result = mw(ctx)
    assert result is None


def test_missing_signature_header_rejects():
    cfg = RequestSigningConfig(enabled=True, secret="s3cr3t")
    mw = make_request_signing_middleware(cfg)
    ctx = make_ctx(request_headers={"X-Timestamp": str(int(time.time()))})
    result = mw(ctx)
    assert result == "reject"
    assert ctx.response_status == 401


def test_missing_timestamp_header_rejects():
    cfg = RequestSigningConfig(enabled=True, secret="s3cr3t")
    mw = make_request_signing_middleware(cfg)
    ctx = make_ctx(request_headers={"X-Signature": "abc"})
    result = mw(ctx)
    assert result == "reject"


def test_invalid_timestamp_rejects():
    cfg = RequestSigningConfig(enabled=True, secret="s3cr3t")
    mw = make_request_signing_middleware(cfg)
    ctx = make_ctx(request_headers={"X-Signature": "abc", "X-Timestamp": "not-a-number"})
    assert mw(ctx) == "reject"
    assert ctx.response_body == b"invalid timestamp"


def test_old_timestamp_rejects():
    cfg = RequestSigningConfig(enabled=True, secret="s3cr3t", max_skew_seconds=30)
    mw = make_request_signing_middleware(cfg)
    old_ts = int(time.time()) - 120
    sig = _sign("s3cr3t", "GET", "/api/data", old_ts)
    ctx = make_ctx(request_headers={"X-Signature": sig, "X-Timestamp": str(old_ts)})
    assert mw(ctx) == "reject"
    assert ctx.response_body == b"timestamp skew too large"


def test_valid_signature_passes():
    cfg = RequestSigningConfig(enabled=True, secret="s3cr3t")
    mw = make_request_signing_middleware(cfg)
    ts = int(time.time())
    sig = _sign("s3cr3t", "GET", "/api/data", ts)
    ctx = make_ctx(request_headers={"X-Signature": sig, "X-Timestamp": str(ts)})
    assert mw(ctx) is None


def test_wrong_signature_rejects():
    cfg = RequestSigningConfig(enabled=True, secret="s3cr3t")
    mw = make_request_signing_middleware(cfg)
    ts = int(time.time())
    ctx = make_ctx(request_headers={"X-Signature": "badhash", "X-Timestamp": str(ts)})
    assert mw(ctx) == "reject"
    assert ctx.response_body == b"invalid signature"
