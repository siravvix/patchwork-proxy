"""Unit tests for patchwork.cors."""
import pytest
from patchwork.cors import CORSConfig, origin_allowed, build_cors_headers


def test_cors_config_defaults():
    cfg = CORSConfig()
    assert cfg.enabled is False
    assert "*" in cfg.allow_origins
    assert cfg.max_age == 600


def test_cors_config_credentials_with_wildcard_raises():
    with pytest.raises(ValueError, match="allow_credentials"):
        CORSConfig(allow_credentials=True, allow_origins=["*"])


def test_cors_config_negative_max_age_raises():
    with pytest.raises(ValueError, match="max_age"):
        CORSConfig(max_age=-1)


def test_cors_config_from_dict():
    cfg = CORSConfig.from_dict({"enabled": True, "allow_origins": ["https://example.com"], "max_age": 300})
    assert cfg.enabled is True
    assert cfg.allow_origins == ["https://example.com"]
    assert cfg.max_age == 300


def test_origin_allowed_wildcard():
    cfg = CORSConfig(allow_origins=["*"])
    assert origin_allowed(cfg, "https://anything.com") is True


def test_origin_allowed_specific_match():
    cfg = CORSConfig(allow_origins=["https://app.example.com"])
    assert origin_allowed(cfg, "https://app.example.com") is True
    assert origin_allowed(cfg, "https://evil.com") is False


def test_origin_allowed_none_returns_false():
    cfg = CORSConfig(allow_origins=["*"])
    assert origin_allowed(cfg, None) is False


def test_build_cors_headers_disabled_returns_empty():
    cfg = CORSConfig(enabled=False)
    headers = build_cors_headers(cfg, "https://example.com")
    assert headers == {}


def test_build_cors_headers_disallowed_origin_returns_empty():
    cfg = CORSConfig(enabled=True, allow_origins=["https://allowed.com"])
    headers = build_cors_headers(cfg, "https://other.com")
    assert headers == {}


def test_build_cors_headers_includes_expected_keys():
    cfg = CORSConfig(enabled=True, allow_origins=["https://app.com"], allow_credentials=True)
    headers = build_cors_headers(cfg, "https://app.com")
    assert "Access-Control-Allow-Origin" in headers
    assert "Access-Control-Allow-Methods" in headers
    assert "Access-Control-Allow-Credentials" in headers
    assert headers["Access-Control-Allow-Credentials"] == "true"


def test_build_cors_headers_expose_headers_omitted_when_empty():
    cfg = CORSConfig(enabled=True, expose_headers=[])
    headers = build_cors_headers(cfg, "https://example.com")
    assert "Access-Control-Expose-Headers" not in headers


def test_build_cors_headers_expose_headers_present():
    cfg = CORSConfig(enabled=True, expose_headers=["X-Request-Id"])
    headers = build_cors_headers(cfg, "https://example.com")
    assert headers.get("Access-Control-Expose-Headers") == "X-Request-Id"
