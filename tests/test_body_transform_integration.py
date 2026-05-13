"""Integration tests for body transform middleware in a full pipeline."""
import json

from patchwork.middleware import MiddlewarePipeline, RequestContext
from patchwork.middleware_body_transform import (
    BodyTransformConfig,
    build_default_body_transform_middleware,
)


def _make_ctx(
    request_body: dict | None = None,
    response_body: dict | None = None,
) -> RequestContext:
    ctx = RequestContext()
    ctx.request = {
        "method": "POST",
        "path": "/api/data",
        "headers": {},
        "body": json.dumps(request_body or {}).encode(),
    }
    ctx.response = {
        "status": 200,
        "headers": {},
        "body": json.dumps(response_body or {}).encode(),
    }
    return ctx


def _make_pipeline(cfg: BodyTransformConfig) -> MiddlewarePipeline:
    pipeline = MiddlewarePipeline()
    build_default_body_transform_middleware(pipeline, cfg)
    return pipeline


def test_pipeline_injects_request_and_response_fields():
    cfg = BodyTransformConfig(
        enabled=True,
        inject_request_fields={"source": "proxy"},
        inject_response_fields={"_proxy": True},
    )
    pipeline = _make_pipeline(cfg)
    ctx = _make_ctx(request_body={"user": "bob"}, response_body={"result": "ok"})
    pipeline.run_pre(ctx)
    pipeline.run_post(ctx)
    req_body = json.loads(ctx.request["body"])
    resp_body = json.loads(ctx.response["body"])
    assert req_body["source"] == "proxy"
    assert resp_body["_proxy"] is True


def test_pipeline_strips_sensitive_fields():
    cfg = BodyTransformConfig(
        enabled=True,
        remove_request_fields=["password", "token"],
        remove_response_fields=["internal_id"],
    )
    pipeline = _make_pipeline(cfg)
    ctx = _make_ctx(
        request_body={"user": "carol", "password": "abc", "token": "xyz"},
        response_body={"data": "value", "internal_id": 99},
    )
    pipeline.run_pre(ctx)
    pipeline.run_post(ctx)
    req_body = json.loads(ctx.request["body"])
    resp_body = json.loads(ctx.response["body"])
    assert "password" not in req_body
    assert "token" not in req_body
    assert "internal_id" not in resp_body
    assert resp_body["data"] == "value"


def test_pipeline_combined_inject_and_remove():
    cfg = BodyTransformConfig(
        enabled=True,
        inject_request_fields={"env": "staging"},
        remove_request_fields=["debug"],
    )
    pipeline = _make_pipeline(cfg)
    ctx = _make_ctx(request_body={"action": "test", "debug": True})
    pipeline.run_pre(ctx)
    body = json.loads(ctx.request["body"])
    assert body["env"] == "staging"
    assert "debug" not in body
    assert body["action"] == "test"


def test_pipeline_disabled_leaves_bodies_unchanged():
    cfg = BodyTransformConfig(
        enabled=False,
        inject_request_fields={"injected": True},
        remove_response_fields=["data"],
    )
    pipeline = _make_pipeline(cfg)
    ctx = _make_ctx(
        request_body={"original": 1},
        response_body={"data": "keep"},
    )
    pipeline.run_pre(ctx)
    pipeline.run_post(ctx)
    assert json.loads(ctx.request["body"]) == {"original": 1}
    assert json.loads(ctx.response["body"]) == {"data": "keep"}
