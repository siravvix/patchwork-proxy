"""Tests for patchwork.auth module."""
import pytest

from patchwork.auth import AuthConfig, extract_api_key, is_authenticated


# --- AuthConfig ---

def test_auth_config_defaults():
    cfg = AuthConfig()
    assert cfg.enabled is False
    assert cfg.header_name == "X-Api-Key"
    assert cfg.query_param == "api_key"
    assert cfg.valid_keys == set()


def test_auth_config_enabled_requires_keys():
    with pytest.raises(ValueError, match="at least one valid key"):
        AuthConfig(enabled=True, valid_keys=set())


def test_auth_config_empty_header_name_raises():
    with pytest.raises(ValueError, match="header_name"):
        AuthConfig(header_name="")


def test_auth_config_from_dict():
    data = {
        "enabled": True,
        "header_name": "Authorization",
        "query_param": "token",
        "valid_keys": ["abc", "xyz"],
    }
    cfg = AuthConfig.from_dict(data)
    assert cfg.enabled is True
    assert cfg.header_name == "Authorization"
    assert cfg.query_param == "token"
    assert cfg.valid_keys == {"abc", "xyz"}


# --- extract_api_key ---

def test_extract_key_from_header():
    cfg = AuthConfig(enabled=True, valid_keys={"k1"})
    key = extract_api_key({"X-Api-Key": "k1"}, {}, cfg)
    assert key == "k1"


def test_extract_key_from_lowercase_header():
    cfg = AuthConfig(enabled=True, valid_keys={"k1"})
    key = extract_api_key({"x-api-key": "k1"}, {}, cfg)
    assert key == "k1"


def test_extract_key_from_query_param():
    cfg = AuthConfig(enabled=True, valid_keys={"k2"})
    key = extract_api_key({}, {"api_key": "k2"}, cfg)
    assert key == "k2"


def test_extract_key_header_takes_precedence():
    cfg = AuthConfig(enabled=True, valid_keys={"header_key", "query_key"})
    key = extract_api_key({"X-Api-Key": "header_key"}, {"api_key": "query_key"}, cfg)
    assert key == "header_key"


def test_extract_key_missing_returns_none():
    cfg = AuthConfig(enabled=True, valid_keys={"k"})
    key = extract_api_key({}, {}, cfg)
    assert key is None


# --- is_authenticated ---

def test_auth_disabled_always_passes():
    cfg = AuthConfig(enabled=False)
    assert is_authenticated(None, cfg) is True
    assert is_authenticated("anything", cfg) is True


def test_valid_key_passes():
    cfg = AuthConfig(enabled=True, valid_keys={"secret"})
    assert is_authenticated("secret", cfg) is True


def test_invalid_key_fails():
    cfg = AuthConfig(enabled=True, valid_keys={"secret"})
    assert is_authenticated("wrong", cfg) is False


def test_none_key_fails_when_enabled():
    cfg = AuthConfig(enabled=True, valid_keys={"secret"})
    assert is_authenticated(None, cfg) is False
