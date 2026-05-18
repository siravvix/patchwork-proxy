"""Unit tests for patchwork.middleware_geo_block."""
from __future__ import annotations

import pytest

from patchwork.middleware import RequestContext
from patchwork.middleware_geo_block import (
    GeoBlockConfig,
    _is_allowed,
    make_geo_block_middleware,
)


def make_ctx(country: str | None = None) -> RequestContext:
    headers = {}
    if country is not None:
        headers["X-Country-Code"] = country
    ctx = RequestContext()
    ctx.request_headers = headers
    return ctx


# --- Config validation ---

def test_config_defaults():
    cfg = GeoBlockConfig()
    assert cfg.enabled is False
    assert cfg.allowlist == []
    assert cfg.blocklist == []
    assert cfg.country_header == "X-Country-Code"
    assert cfg.reject_status == 403
    assert cfg.unknown_country_policy == "allow"


def test_config_allowlist_and_blocklist_raises():
    with pytest.raises(ValueError, match="not both"):
        GeoBlockConfig(allowlist=["US"], blocklist=["CN"])


def test_config_invalid_reject_status_raises():
    with pytest.raises(ValueError, match="reject_status"):
        GeoBlockConfig(reject_status=200)


def test_config_empty_header_raises():
    with pytest.raises(ValueError, match="country_header"):
        GeoBlockConfig(country_header="")


def test_config_invalid_unknown_policy_raises():
    with pytest.raises(ValueError, match="unknown_country_policy"):
        GeoBlockConfig(unknown_country_policy="deny")


def test_config_from_dict():
    cfg = GeoBlockConfig.from_dict(
        {"enabled": True, "allowlist": ["us", "gb"], "reject_status": 451}
    )
    assert cfg.enabled is True
    assert cfg.allowlist == ["US", "GB"]
    assert cfg.reject_status == 451


# --- _is_allowed logic ---

def test_allowlist_permits_listed_country():
    cfg = GeoBlockConfig(allowlist=["US", "GB"])
    assert _is_allowed(cfg, "US") is True


def test_allowlist_blocks_unlisted_country():
    cfg = GeoBlockConfig(allowlist=["US"])
    assert _is_allowed(cfg, "DE") is False


def test_blocklist_blocks_listed_country():
    cfg = GeoBlockConfig(blocklist=["CN", "RU"])
    assert _is_allowed(cfg, "CN") is False


def test_blocklist_permits_unlisted_country():
    cfg = GeoBlockConfig(blocklist=["CN"])
    assert _is_allowed(cfg, "US") is True


def test_unknown_country_allow_policy():
    cfg = GeoBlockConfig(unknown_country_policy="allow")
    assert _is_allowed(cfg, None) is True


def test_unknown_country_block_policy():
    cfg = GeoBlockConfig(unknown_country_policy="block")
    assert _is_allowed(cfg, None) is False


# --- Middleware behaviour ---

def test_middleware_disabled_passes_all():
    mw = make_geo_block_middleware(GeoBlockConfig(enabled=False))
    ctx = make_ctx("CN")
    result = mw(ctx)
    assert result.response_status is None


def test_middleware_blocks_disallowed_country():
    cfg = GeoBlockConfig(enabled=True, allowlist=["US"])
    mw = make_geo_block_middleware(cfg)
    ctx = make_ctx("CN")
    result = mw(ctx)
    assert result.response_status == 403
    assert result.response_body == b"Forbidden"


def test_middleware_allows_listed_country():
    cfg = GeoBlockConfig(enabled=True, allowlist=["US"])
    mw = make_geo_block_middleware(cfg)
    ctx = make_ctx("US")
    result = mw(ctx)
    assert result.response_status is None


def test_middleware_custom_reject_status():
    cfg = GeoBlockConfig(enabled=True, blocklist=["CN"], reject_status=451)
    mw = make_geo_block_middleware(cfg)
    ctx = make_ctx("CN")
    result = mw(ctx)
    assert result.response_status == 451
