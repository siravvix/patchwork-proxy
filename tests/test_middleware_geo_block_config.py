"""Unit tests for patchwork.middleware_geo_block_config."""
from __future__ import annotations

from patchwork.middleware_geo_block_config import (
    GeoBlockMiddlewareConfig,
    geo_block_config_from_proxy_config,
)


def test_from_dict_defaults():
    cfg = GeoBlockMiddlewareConfig.from_dict({})
    assert cfg.geo_block.enabled is False
    assert cfg.geo_block.allowlist == []
    assert cfg.geo_block.blocklist == []


def test_from_dict_full():
    data = {
        "geo_block": {
            "enabled": True,
            "blocklist": ["cn", "ru"],
            "reject_status": 451,
            "unknown_country_policy": "block",
        }
    }
    cfg = GeoBlockMiddlewareConfig.from_dict(data)
    assert cfg.geo_block.enabled is True
    assert cfg.geo_block.blocklist == ["CN", "RU"]
    assert cfg.geo_block.reject_status == 451
    assert cfg.geo_block.unknown_country_policy == "block"


def test_as_dict_round_trips():
    data = {
        "geo_block": {
            "enabled": True,
            "allowlist": ["US", "GB"],
            "blocklist": [],
            "country_header": "X-Country-Code",
            "reject_status": 403,
            "unknown_country_policy": "allow",
        }
    }
    cfg = GeoBlockMiddlewareConfig.from_dict(data)
    assert cfg.as_dict() == data


def test_geo_block_config_from_proxy_config_present():
    class FakeProxy:
        extra = {"geo_block": {"enabled": True, "blocklist": ["CN"]}}

    cfg = geo_block_config_from_proxy_config(FakeProxy())
    assert cfg.geo_block.enabled is True
    assert "CN" in cfg.geo_block.blocklist


def test_geo_block_config_from_proxy_config_absent():
    class FakeProxy:
        extra = {}

    cfg = geo_block_config_from_proxy_config(FakeProxy())
    assert cfg.geo_block.enabled is False
