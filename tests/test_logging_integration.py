"""Integration tests: logging middleware wired into MiddlewarePipeline."""

from __future__ import annotations

from unittest.mock import patch

from patchwork.middleware import MiddlewarePipeline, RequestContext
from patchwork.middleware_logging import build_default_logging_middleware


def _make_pipeline(**kwargs) -> MiddlewarePipeline:
    pipeline = MiddlewarePipeline()
    build_default_logging_middleware(pipeline, **kwargs)
    return pipeline


def _make_ctx(method: str = "POST", path: str = "/submit") -> RequestContext:
    return RequestContext(request={"method": method, "path": path, "headers": {}, "target": "http://backend"})


def test_pipeline_logs_request_and_response():
    pipeline = _make_pipeline()
    ctx = _make_ctx()

    with patch("patchwork.middleware_logging.logger") as mock_log:
        ctx = pipeline.run_pre(ctx)
        ctx.response = {"status": 201, "headers": {}, "body": "created"}
        pipeline.run_post(ctx)

    calls = [c[0][0] for c in mock_log.info.call_args_list]
    events = [c["event"] for c in calls]
    assert "request_received" in events
    assert "request_completed" in events


def test_pipeline_elapsed_ms_is_positive():
    pipeline = _make_pipeline()
    ctx = _make_ctx()

    with patch("patchwork.middleware_logging.logger") as mock_log:
        ctx = pipeline.run_pre(ctx)
        ctx.response = {"status": 200, "headers": {}, "body": ""}
        pipeline.run_post(ctx)

    post_call = [
        c[0][0]
        for c in mock_log.info.call_args_list
        if c[0][0].get("event") == "request_completed"
    ][0]
    assert post_call["elapsed_ms"] >= 0


def test_pipeline_full_headers_and_body_logging():
    pipeline = _make_pipeline(log_request_headers=True, log_response_headers=True, log_body=True)
    ctx = _make_ctx()
    ctx.request["headers"] = {"X-Request-Id": "abc"}

    with patch("patchwork.middleware_logging.logger") as mock_log:
        ctx = pipeline.run_pre(ctx)
        ctx.response = {"status": 200, "headers": {"X-Trace": "xyz"}, "body": "data"}
        pipeline.run_post(ctx)

    calls = {c[0][0]["event"]: c[0][0] for c in mock_log.info.call_args_list}
    assert calls["request_received"]["request_headers"]["X-Request-Id"] == "abc"
    assert calls["request_completed"]["response_headers"]["X-Trace"] == "xyz"
    assert calls["request_completed"]["response_body"] == "data"


def test_pipeline_route_id_in_both_events():
    pipeline = _make_pipeline()
    ctx = _make_ctx(method="DELETE", path="/resource/42")

    with patch("patchwork.middleware_logging.logger") as mock_log:
        ctx = pipeline.run_pre(ctx)
        ctx.response = {"status": 204, "headers": {}, "body": ""}
        pipeline.run_post(ctx)

    for call in mock_log.info.call_args_list:
        assert call[0][0]["route"] == "DELETE /resource/42"
