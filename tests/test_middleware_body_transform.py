"""Unit tests for middleware_body_transform."""
import json
import pytest

from patchwork.middleware import RequestContext
from patchwork.middleware_body_transform import (
    BodyTransformConfig,
    _transform_json,
    make_body_transform_middleware,
)


def make_ctx(
    request_body: bytes = b"",
    response_body: bytes = b"",
    method: str = "POST",
) -> RequestContext:
    ctx = RequestContext()
    ctx.request = {"method": method, "path": "/test", "headers": {}, "body": request_body}
    ctx.response = {"status": 200, "headers": {}, "body": response_body}
    return ctx


# --- Config tests ---

def test_config_defaults():
    cfg = BodyTransformConfig()
    assert cfg.enabled is False
    assert cfg.inject_request_fields == {}
    assert cfg.remove_request_fields == []
    assert cfg.inject_response_fields == {}
    assert cfg.remove_response_fields == []


def test_config_invalid_inject_raises():
    with pytest.raises(ValueError):
        BodyTransformConfig(inject_request_fields=["bad"])


def test_config_invalid_remove_raises():
    with pytest.raises(ValueError):
        BodyTransformConfig(remove_request_fields={"bad": 1})


def test_config_from_dict():
    cfg = BodyTransformConfig.from_dict({
        "enabled": True,
        "inject_request_fields": {"env": "prod"},
        "remove_request_fields": ["secret"],
    })
    assert cfg.enabled is True
    assert cfg.inject_request_fields == {"env": "prod"}
    assert cfg.remove_request_fields == ["secret"]


# --- _transform_json tests ---

def test_transform_json_injects_field():
    body = json.dumps({"a": 1}).encode()
    result = _transform_json(body, {"b": 2}, [])
    assert json.loads(result) == {"a": 1, "b": 2}


def test_transform_json_removes_field():
    body = json.dumps({"a": 1, "secret": "x"}).encode()
    result = _transform_json(body, {}, ["secret"])
    assert json.loads(result) == {"a": 1}


def test_transform_json_invalid_body_unchanged():
    body = b"not json"
    result = _transform_json(body, {"x": 1}, [])
    assert result == b"not json"


def test_transform_json_array_unchanged():
    body = json.dumps([1, 2, 3]).encode()
    result = _transform_json(body, {"x": 1}, [])
    assert json.loads(result) == [1, 2, 3]


# --- Middleware tests ---

def test_pre_middleware_injects_request_field():
    cfg = BodyTransformConfig(enabled=True, inject_request_fields={"env": "test"})
    pre, _ = make_body_transform_middleware(cfg)
    ctx = make_ctx(request_body=json.dumps({"user": "alice"}).encode())
    pre(ctx)
    assert json.loads(ctx.request["body"]) == {"user": "alice", "env": "test"}


def test_pre_middleware_removes_request_field():
    cfg = BodyTransformConfig(enabled=True, remove_request_fields=["password"])
    pre, _ = make_body_transform_middleware(cfg)
    ctx = make_ctx(request_body=json.dumps({"user": "alice", "password": "s3cr3t"}).encode())
    pre(ctx)
    assert "password" not in json.loads(ctx.request["body"])


def test_post_middleware_injects_response_field():
    cfg = BodyTransformConfig(enabled=True, inject_response_fields={"_version": "1"})
    _, post = make_body_transform_middleware(cfg)
    ctx = make_ctx(response_body=json.dumps({"id": 42}).encode())
    post(ctx)
    assert json.loads(ctx.response["body"])["_version"] == "1"


def test_post_middleware_removes_response_field():
    cfg = BodyTransformConfig(enabled=True, remove_response_fields=["internal"])
    _, post = make_body_transform_middleware(cfg)
    ctx = make_ctx(response_body=json.dumps({"data": "ok", "internal": True}).encode())
    post(ctx)
    assert "internal" not in json.loads(ctx.response["body"])


def test_disabled_cfg_does_nothing():
    cfg = BodyTransformConfig(enabled=False, inject_request_fields={"x": 1})
    pre, post = make_body_transform_middleware(cfg)
    body = json.dumps({"a": 1}).encode()
    ctx = make_ctx(request_body=body, response_body=body)
    pre(ctx)
    post(ctx)
    assert ctx.request["body"] == body
    assert ctx.response["body"] == body
