"""Unit tests for patchwork.middleware_tls_verify_config."""
from patchwork.middleware_tls_verify_config import (
    TLSVerifyMiddlewareConfig,
    tls_verify_config_from_proxy_config,
)


def test_from_dict_defaults():
    cfg = TLSVerifyMiddlewareConfig.from_dict({})
    assert cfg.tls_verify.enabled is False
    assert cfg.tls_verify.forwarded_proto_header == "X-Forwarded-Proto"
    assert cfg.tls_verify.reject_status == 403


def test_from_dict_full():
    raw = {
        "tls_verify": {
            "enabled": True,
            "forwarded_proto_header": "X-Real-Proto",
            "reject_status": 426,
            "reject_reason": "Must use TLS",
        }
    }
    cfg = TLSVerifyMiddlewareConfig.from_dict(raw)
    assert cfg.tls_verify.enabled is True
    assert cfg.tls_verify.forwarded_proto_header == "X-Real-Proto"
    assert cfg.tls_verify.reject_status == 426
    assert cfg.tls_verify.reject_reason == "Must use TLS"


def test_as_dict_round_trips():
    raw = {
        "tls_verify": {
            "enabled": True,
            "forwarded_proto_header": "X-Forwarded-Proto",
            "reject_status": 403,
            "reject_reason": "HTTPS required",
        }
    }
    cfg = TLSVerifyMiddlewareConfig.from_dict(raw)
    assert cfg.as_dict() == raw


def test_tls_verify_config_from_proxy_config_present():
    proxy_cfg = {"tls_verify": {"enabled": True}}
    result = tls_verify_config_from_proxy_config(proxy_cfg)
    assert result.tls_verify.enabled is True


def test_tls_verify_config_from_proxy_config_absent():
    result = tls_verify_config_from_proxy_config({})
    assert result.tls_verify.enabled is False
