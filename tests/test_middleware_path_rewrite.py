"""Tests for patchwork.middleware_path_rewrite."""

import pytest

from patchwork.middleware import MiddlewarePipeline, RequestContext
from patchwork.middleware_path_rewrite import (
    PathRewriteConfig,
    PathRewriteRule,
    build_default_path_rewrite_middleware,
    make_path_rewrite_middleware,
)


def make_ctx(path: str = "/api/v1/users", method: str = "GET") -> RequestContext:
    return RequestContext(
        request={"path": path, "method": method, "headers": {}},
        response={},
        meta={},
    )


# --- PathRewriteRule ---

def test_rule_invalid_pattern_raises():
    with pytest.raises(ValueError, match="invalid regex"):
        PathRewriteRule(pattern="[", replacement="")


def test_rule_empty_pattern_raises():
    with pytest.raises(ValueError, match="must not be empty"):
        PathRewriteRule(pattern="", replacement="/new")


def test_rule_matches_returns_true_for_matching_path():
    rule = PathRewriteRule(pattern=r"^/api/v1", replacement="/v1")
    assert rule.matches("/api/v1/users") is True


def test_rule_matches_returns_false_for_non_matching_path():
    rule = PathRewriteRule(pattern=r"^/api/v2", replacement="/v2")
    assert rule.matches("/api/v1/users") is False


def test_rule_apply_substitutes_path():
    rule = PathRewriteRule(pattern=r"^/api/v1", replacement="/v1")
    assert rule.apply("/api/v1/users") == "/v1/users"


# --- PathRewriteConfig ---

def test_config_defaults():
    cfg = PathRewriteConfig()
    assert cfg.enabled is False
    assert cfg.rules == []


def test_config_enabled_without_rules_raises():
    with pytest.raises(ValueError, match="no rules are defined"):
        PathRewriteConfig(enabled=True, rules=[])


def test_config_from_dict():
    data = {
        "enabled": True,
        "rules": [{"pattern": r"^/old", "replacement": "/new"}],
    }
    cfg = PathRewriteConfig.from_dict(data)
    assert cfg.enabled is True
    assert len(cfg.rules) == 1
    assert cfg.rules[0].apply("/old/path") == "/new/path"


def test_config_from_dict_disabled_no_rules():
    cfg = PathRewriteConfig.from_dict({"enabled": False})
    assert cfg.enabled is False
    assert cfg.rules == []


# --- make_path_rewrite_middleware ---

def test_middleware_disabled_does_not_rewrite():
    cfg = PathRewriteConfig(enabled=False)
    mw = make_path_rewrite_middleware(cfg)
    ctx = make_ctx("/api/v1/users")
    mw(ctx)
    assert ctx.request["path"] == "/api/v1/users"
    assert "path_rewritten" not in ctx.meta


def test_middleware_rewrites_matching_path():
    rule = PathRewriteRule(pattern=r"^/api/v1", replacement="/v1")
    cfg = PathRewriteConfig(enabled=True, rules=[rule])
    mw = make_path_rewrite_middleware(cfg)
    ctx = make_ctx("/api/v1/users")
    mw(ctx)
    assert ctx.request["path"] == "/v1/users"
    assert ctx.meta["path_rewritten"] is True
    assert ctx.meta["original_path"] == "/api/v1/users"


def test_middleware_first_match_wins():
    rules = [
        PathRewriteRule(pattern=r"^/api", replacement="/first"),
        PathRewriteRule(pattern=r"^/api", replacement="/second"),
    ]
    cfg = PathRewriteConfig(enabled=True, rules=rules)
    mw = make_path_rewrite_middleware(cfg)
    ctx = make_ctx("/api/data")
    mw(ctx)
    assert ctx.request["path"] == "/first/data"


def test_middleware_no_match_leaves_path_unchanged():
    rule = PathRewriteRule(pattern=r"^/internal", replacement="/private")
    cfg = PathRewriteConfig(enabled=True, rules=[rule])
    mw = make_path_rewrite_middleware(cfg)
    ctx = make_ctx("/api/v1/users")
    mw(ctx)
    assert ctx.request["path"] == "/api/v1/users"
    assert "path_rewritten" not in ctx.meta


def test_build_default_registers_pre_middleware():
    rule = PathRewriteRule(pattern=r"^/legacy", replacement="/modern")
    cfg = PathRewriteConfig(enabled=True, rules=[rule])
    pipeline = MiddlewarePipeline()
    build_default_path_rewrite_middleware(pipeline, cfg)
    ctx = make_ctx("/legacy/endpoint")
    pipeline.run_pre(ctx)
    assert ctx.request["path"] == "/modern/endpoint"
