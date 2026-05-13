"""Tests for TracingMiddlewareConfig and tracing_config_from_proxy_config."""
import pytest

from patchwork.middleware_tracing_config import (
    TracingMiddlewareConfig,
    tracing_config_from_proxy_config,
)


def test_from_dict_defaults():
    cfg = TracingMiddlewareConfig.from_dict({})
    assert cfg.tracing.enabled is False
    assert cfg.tracing.trace_id_header == "X-Trace-Id"


def test_from_dict_full():
    cfg = TracingMiddlewareConfig.from_dict({
        "tracing": {
            "enabled": True,
            "trace_id_header": "Traceparent",
            "span_id_header": "Tracestate",
            "propagate_trace": False,
            "propagate_span": True,
        }
    })
    assert cfg.tracing.enabled is True
    assert cfg.tracing.trace_id_header == "Traceparent"
    assert cfg.tracing.propagate_trace is False
    assert cfg.tracing.propagate_span is True


def test_as_dict_round_trips():
    original = {
        "tracing": {
            "enabled": True,
            "trace_id_header": "X-Trace-Id",
            "span_id_header": "X-Span-Id",
            "propagate_trace": True,
            "propagate_span": False,
        }
    }
    cfg = TracingMiddlewareConfig.from_dict(original)
    assert cfg.as_dict() == original


def test_tracing_config_from_proxy_config_present():
    proxy_cfg = {"tracing": {"enabled": True}}
    cfg = tracing_config_from_proxy_config(proxy_cfg)
    assert cfg is not None
    assert cfg.enabled is True


def test_tracing_config_from_proxy_config_absent():
    proxy_cfg = {"routes": []}
    cfg = tracing_config_from_proxy_config(proxy_cfg)
    assert cfg is None


def test_tracing_config_from_proxy_config_empty_section():
    proxy_cfg = {"tracing": {}}
    cfg = tracing_config_from_proxy_config(proxy_cfg)
    assert cfg is not None
    assert cfg.enabled is False
