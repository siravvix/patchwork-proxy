"""Tests for patchwork.config module."""

import json
import os
import tempfile

import pytest

from patchwork.config import ProxyConfig, RouteRule, load_config


SAMPLE_CONFIG = {
    "listen_port": 9090,
    "log_level": "DEBUG",
    "routes": [
        {"prefix": "/api", "target": "http://localhost:3000", "strip_prefix": True},
        {"prefix": "/static", "target": "http://localhost:4000", "methods": ["GET"]},
    ],
}


def test_route_rule_matches_path():
    rule = RouteRule(prefix="/api", target="http://backend")
    assert rule.matches("/api/users", "GET")
    assert not rule.matches("/other", "GET")


def test_route_rule_method_filter():
    rule = RouteRule(prefix="/api", target="http://backend", methods=["GET"])
    assert rule.matches("/api/x", "GET")
    assert not rule.matches("/api/x", "POST")


def test_route_rule_strip_prefix():
    rule = RouteRule(prefix="/api", target="http://backend", strip_prefix=True)
    assert rule.rewrite("/api/users") == "/users"
    assert rule.rewrite("/api") == "/"


def test_route_rule_no_strip_prefix():
    rule = RouteRule(prefix="/api", target="http://backend", strip_prefix=False)
    assert rule.rewrite("/api/users") == "/api/users"


def test_proxy_config_from_dict():
    config = ProxyConfig.from_dict(SAMPLE_CONFIG)
    assert config.listen_port == 9090
    assert config.log_level == "DEBUG"
    assert len(config.routes) == 2


def test_proxy_config_match_route():
    config = ProxyConfig.from_dict(SAMPLE_CONFIG)
    rule = config.match_route("/api/data", "POST")
    assert rule is not None
    assert rule.target == "http://localhost:3000"


def test_proxy_config_no_match():
    config = ProxyConfig.from_dict(SAMPLE_CONFIG)
    assert config.match_route("/unknown", "GET") is None


def test_load_config_from_file():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as fh:
        json.dump(SAMPLE_CONFIG, fh)
        path = fh.name
    try:
        config = load_config(path)
        assert config.listen_port == 9090
    finally:
        os.unlink(path)


def test_load_config_missing_file():
    with pytest.raises(FileNotFoundError):
        load_config("/nonexistent/config.json")
