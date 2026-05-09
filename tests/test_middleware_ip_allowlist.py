"""Unit tests for the IP allowlist middleware."""
import pytest

from patchwork.middleware import RequestContext
from patchwork.middleware_ip_allowlist import (
    IPAllowlistConfig,
    _ip_allowed,
    _parse_client_ip,
    make_ip_allowlist_middleware,
)


def make_ctx(
    headers: dict | None = None,
    metadata: dict | None = None,
) -> RequestContext:
    return RequestContext(
        method="GET",
        path="/api/data",
        request_headers=headers or {},
        metadata=metadata or {},
    )


# ── config validation ──────────────────────────────────────────────────────────

def test_config_defaults():
    cfg = IPAllowlistConfig()
    assert cfg.enabled is False
    assert cfg.allowed_cidrs == []
    assert cfg.header == "X-Forwarded-For"


def test_config_enabled_without_cidrs_raises():
    with pytest.raises(ValueError, match="no CIDRs"):
        IPAllowlistConfig(enabled=True, allowed_cidrs=[])


def test_config_invalid_cidr_raises():
    with pytest.raises(ValueError, match="Invalid CIDR"):
        IPAllowlistConfig(enabled=True, allowed_cidrs=["not-a-cidr"])


def test_config_empty_header_raises():
    with pytest.raises(ValueError, match="header"):
        IPAllowlistConfig(enabled=True, allowed_cidrs=["10.0.0.0/8"], header="")


def test_config_from_dict():
    cfg = IPAllowlistConfig.from_dict(
        {"enabled": True, "allowed_cidrs": ["192.168.1.0/24"], "header": "X-Real-IP"}
    )
    assert cfg.enabled is True
    assert cfg.allowed_cidrs == ["192.168.1.0/24"]
    assert cfg.header == "X-Real-IP"


# ── _ip_allowed helper ─────────────────────────────────────────────────────────

def test_ip_allowed_within_cidr():
    assert _ip_allowed("10.0.0.5", ["10.0.0.0/8"]) is True


def test_ip_not_allowed_outside_cidr():
    assert _ip_allowed("172.16.0.1", ["10.0.0.0/8"]) is False


def test_ip_allowed_multiple_cidrs():
    assert _ip_allowed("192.168.5.10", ["10.0.0.0/8", "192.168.0.0/16"]) is True


def test_ip_invalid_string_returns_false():
    assert _ip_allowed("not-an-ip", ["10.0.0.0/8"]) is False


# ── _parse_client_ip helper ────────────────────────────────────────────────────

def test_parse_client_ip_from_header():
    ctx = make_ctx(headers={"X-Forwarded-For": "1.2.3.4, 5.6.7.8"})
    assert _parse_client_ip(ctx, "X-Forwarded-For") == "1.2.3.4"


def test_parse_client_ip_falls_back_to_remote_addr():
    ctx = make_ctx(metadata={"remote_addr": "9.9.9.9"})
    assert _parse_client_ip(ctx, "X-Forwarded-For") == "9.9.9.9"


def test_parse_client_ip_returns_none_when_absent():
    ctx = make_ctx()
    assert _parse_client_ip(ctx, "X-Forwarded-For") is None


# ── middleware behaviour ───────────────────────────────────────────────────────

def test_middleware_disabled_allows_all():
    cfg = IPAllowlistConfig(enabled=False)
    mw = make_ip_allowlist_middleware(cfg)
    ctx = make_ctx(headers={"X-Forwarded-For": "1.2.3.4"})
    result = mw(ctx)
    assert "ip_blocked" not in result.metadata


def test_middleware_allows_matching_ip():
    cfg = IPAllowlistConfig(enabled=True, allowed_cidrs=["10.0.0.0/8"])
    mw = make_ip_allowlist_middleware(cfg)
    ctx = make_ctx(headers={"X-Forwarded-For": "10.1.2.3"})
    result = mw(ctx)
    assert result.metadata["ip_blocked"] is False


def test_middleware_blocks_non_matching_ip():
    cfg = IPAllowlistConfig(enabled=True, allowed_cidrs=["10.0.0.0/8"])
    mw = make_ip_allowlist_middleware(cfg)
    ctx = make_ctx(headers={"X-Forwarded-For": "172.16.0.1"})
    result = mw(ctx)
    assert result.metadata["ip_blocked"] is True
    assert "block_reason" in result.metadata


def test_middleware_blocks_when_no_ip_found():
    cfg = IPAllowlistConfig(enabled=True, allowed_cidrs=["10.0.0.0/8"])
    mw = make_ip_allowlist_middleware(cfg)
    ctx = make_ctx()  # no headers, no remote_addr
    result = mw(ctx)
    assert result.metadata["ip_blocked"] is True
