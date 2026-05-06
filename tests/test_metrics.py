"""Tests for patchwork.metrics collector."""

import pytest
from patchwork.metrics import MetricsCollector


def test_record_increments_requests():
    m = MetricsCollector()
    m.record("GET /api", 42.0)
    snap = m.snapshot()
    assert snap["GET /api"].requests == 1
    assert snap["GET /api"].total_ms == 42.0
    assert snap["GET /api"].errors == 0


def test_record_error_flag():
    m = MetricsCollector()
    m.record("POST /upload", 100.0, is_error=True)
    snap = m.snapshot()
    assert snap["POST /upload"].errors == 1


def test_avg_ms_calculated_correctly():
    m = MetricsCollector()
    m.record("GET /", 100.0)
    m.record("GET /", 200.0)
    snap = m.snapshot()
    assert snap["GET /"].avg_ms == pytest.approx(150.0)


def test_avg_ms_zero_when_no_requests():
    from patchwork.metrics import RouteStats
    s = RouteStats()
    assert s.avg_ms == 0.0


def test_reset_clears_all_stats():
    m = MetricsCollector()
    m.record("GET /health", 5.0)
    m.reset()
    assert m.snapshot() == {}


def test_snapshot_is_copy():
    m = MetricsCollector()
    m.record("GET /foo", 10.0)
    snap = m.snapshot()
    snap["GET /foo"].requests = 999
    assert m.snapshot()["GET /foo"].requests == 1


def test_summary_contains_route_key():
    m = MetricsCollector()
    m.record("DELETE /item", 20.0)
    summary = m.summary()
    assert "DELETE /item" in summary
    assert "1 req" in summary


def test_thread_safety():
    import threading
    m = MetricsCollector()
    threads = [threading.Thread(target=lambda: m.record("GET /stress", 1.0)) for _ in range(100)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert m.snapshot()["GET /stress"].requests == 100
