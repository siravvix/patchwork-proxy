"""Tests for JWT authentication middleware."""
from __future__ import annotations

import base64
import hashlib
import hmac
import json

import pytest

from patchwork.middleware import RequestContext
from patchwork.middleware_jwt import (
    JWTConfig,
    decode_jwt,
    make_jwt_middleware,
)


def _make_ctx(headers: dict | None = None) -> RequestContext:
    ctx = RequestContext()
    ctx.request_headers = headers or {}
    ctx.response_headers = {}
    ctx.meta = {}
    return ctx


def _make_token(payload: dict, secret: str, alg: str = "HS256") -> str:
    header = base64.urlsafe_b64encode(json.dumps({"alg": alg, "typ": "JWT"}).encode()).rstrip(b"=").decode()
    body = base64.urlsafe_b64encode(json.dumps(payload).encode()).rstrip(b"=").decode()
    msg = f"{header}.{body}".encode()
    sig = hmac.new(secret.encode(), msg, hashlib.sha256).digest()
    sig_b64 = base64.urlsafe_b64encode(sig).rstrip(b"=").decode()
    return f"{header}.{body}.{sig_b64}"


# --- JWTConfig ---

def test_config_defaults():
    cfg = JWTConfig()
    assert cfg.enabled is False
    assert cfg.algorithms == ["HS256"]
    assert cfg.header_name == "Authorization"
    assert cfg.prefix == "Bearer"


def test_config_enabled_requires_secret():
    with pytest.raises(ValueError, match="secret"):
        JWTConfig(enabled=True, secret="")


def test_config_empty_header_raises():
    with pytest.raises(ValueError, match="header_name"):
        JWTConfig(header_name="")


def test_config_from_dict():
    cfg = JWTConfig.from_dict({"enabled": True, "secret": "s3cr3t", "algorithms": ["HS256"]})
    assert cfg.enabled is True
    assert cfg.secret == "s3cr3t"


# --- decode_jwt ---

def test_decode_valid_token():
    token = _make_token({"sub": "alice"}, "mysecret")
    payload = decode_jwt(token, "mysecret", ["HS256"])
    assert payload is not None
    assert payload["sub"] == "alice"


def test_decode_wrong_secret_returns_none():
    token = _make_token({"sub": "alice"}, "mysecret")
    assert decode_jwt(token, "wrongsecret", ["HS256"]) is None


def test_decode_wrong_algorithm_returns_none():
    token = _make_token({"sub": "alice"}, "mysecret")
    assert decode_jwt(token, "mysecret", ["RS256"]) is None


def test_decode_malformed_token_returns_none():
    assert decode_jwt("not.a.valid.token.here", "secret", ["HS256"]) is None


# --- make_jwt_middleware ---

def test_middleware_disabled_passes_all():
    cfg = JWTConfig(enabled=False)
    mw = make_jwt_middleware(cfg)
    ctx = _make_ctx()
    result = mw(ctx)
    assert result is ctx
    assert not hasattr(result, "response_status") or result.response_status is None


def test_middleware_valid_token_sets_meta():
    secret = "topsecret"
    token = _make_token({"sub": "bob"}, secret)
    cfg = JWTConfig(enabled=True, secret=secret)
    mw = make_jwt_middleware(cfg)
    ctx = _make_ctx({"Authorization": f"Bearer {token}"})
    result = mw(ctx)
    assert result.meta["jwt_payload"]["sub"] == "bob"
    assert result.request_headers.get("X-JWT-Sub") == "bob"


def test_middleware_missing_header_returns_401():
    cfg = JWTConfig(enabled=True, secret="s")
    mw = make_jwt_middleware(cfg)
    ctx = _make_ctx()
    result = mw(ctx)
    assert result.response_status == 401


def test_middleware_invalid_token_returns_401():
    cfg = JWTConfig(enabled=True, secret="s")
    mw = make_jwt_middleware(cfg)
    ctx = _make_ctx({"Authorization": "Bearer bad.token.here"})
    result = mw(ctx)
    assert result.response_status == 401


def test_middleware_no_claim_header_when_none():
    secret = "topsecret"
    token = _make_token({"sub": "carol"}, secret)
    cfg = JWTConfig(enabled=True, secret=secret, claim_header=None)
    mw = make_jwt_middleware(cfg)
    ctx = _make_ctx({"Authorization": f"Bearer {token}"})
    result = mw(ctx)
    assert "X-JWT-Sub" not in result.request_headers
