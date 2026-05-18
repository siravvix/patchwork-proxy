"""Tests for the request signing config wrapper."""
from patchwork.middleware_request_signing_config import (
    RequestSigningMiddlewareConfig,
    request_signing_config_from_proxy_config,
)


def test_from_dict_defaults():
    cfg = RequestSigningMiddlewareConfig.from_dict({})
    assert cfg.enabled is False
    assert cfg.secret == ""
    assert cfg.header_name == "X-Signature"
    assert cfg.timestamp_header == "X-Timestamp"
    assert cfg.max_skew_seconds == 30
    assert cfg.reject_status == 401


def test_from_dict_full():
    cfg = RequestSigningMiddlewareConfig.from_dict({
        "enabled": True,
        "secret": "topsecret",
        "header_name": "X-Sig",
        "timestamp_header": "X-TS",
        "max_skew_seconds": 60,
        "reject_status": 403,
    })
    assert cfg.enabled is True
    assert cfg.secret == "topsecret"
    assert cfg.header_name == "X-Sig"
    assert cfg.timestamp_header == "X-TS"
    assert cfg.max_skew_seconds == 60
    assert cfg.reject_status == 403


def test_as_dict_round_trips():
    original = {
        "enabled": True,
        "secret": "abc",
        "header_name": "X-Signature",
        "timestamp_header": "X-Timestamp",
        "max_skew_seconds": 30,
        "reject_status": 401,
    }
    cfg = RequestSigningMiddlewareConfig.from_dict(original)
    assert cfg.as_dict() == original


def test_request_signing_config_from_proxy_config_present():
    proxy_cfg = {"request_signing": {"enabled": True, "secret": "xyz", "max_skew_seconds": 10}}
    cfg = request_signing_config_from_proxy_config(proxy_cfg)
    assert cfg.enabled is True
    assert cfg.secret == "xyz"
    assert cfg.max_skew_seconds == 10


def test_request_signing_config_from_proxy_config_absent():
    cfg = request_signing_config_from_proxy_config({})
    assert cfg.enabled is False
    assert cfg.secret == ""
