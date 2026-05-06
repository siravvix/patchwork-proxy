"""Tests for patchwork.watcher module."""

import json
import os
import tempfile
import time

from patchwork.watcher import ConfigWatcher


def _write_config(path: str, data: dict) -> None:
    with open(path, "w") as fh:
        json.dump(data, fh)


def test_watcher_detects_change():
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False
    ) as fh:
        json.dump({"routes": []}, fh)
        path = fh.name

    events = []

    def on_change(p: str) -> None:
        events.append(p)

    watcher = ConfigWatcher(path, on_change, poll_interval=0.1)
    watcher.start()
    try:
        time.sleep(0.15)  # let watcher settle
        _write_config(path, {"routes": [{"prefix": "/x", "target": "http://x"}]})
        time.sleep(0.4)  # allow at least one poll cycle
        assert len(events) >= 1
        assert events[0] == path
    finally:
        watcher.stop()
        os.unlink(path)


def test_watcher_no_spurious_events():
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False
    ) as fh:
        json.dump({"routes": []}, fh)
        path = fh.name

    events = []
    watcher = ConfigWatcher(path, lambda p: events.append(p), poll_interval=0.1)
    watcher.start()
    try:
        time.sleep(0.5)  # no writes
        assert events == []
    finally:
        watcher.stop()
        os.unlink(path)


def test_watcher_stops_cleanly():
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False
    ) as fh:
        json.dump({}, fh)
        path = fh.name
    watcher = ConfigWatcher(path, lambda p: None, poll_interval=0.1)
    watcher.start()
    watcher.stop()
    assert not watcher._thread.is_alive()
    os.unlink(path)
