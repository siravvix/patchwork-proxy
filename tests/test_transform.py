"""Tests for patchwork.transform."""
import pytest

from patchwork.transform import (
    TransformConfig,
    apply_request_transforms,
    apply_response_transforms,
)


# ---------------------------------------------------------------------------
# TransformConfig construction
# ---------------------------------------------------------------------------

def test_transform_config_defaults():
    cfg = TransformConfig()
    assert cfg.set_request_headers == {}
    assert cfg.remove_request_headers == []
    assert cfg.set_response_headers == {}
    assert cfg.remove_response_headers == []


def test_transform_config_from_dict():
    data = {
        "set_request_headers": {"X-Real-IP": "127.0.0.1"},
        "remove_request_headers": ["Cookie"],
        "set_response_headers": {"X-Powered-By": "patchwork"},
        "remove_response_headers": ["Server"],
    }
    cfg = TransformConfig.from_dict(data)
    assert cfg.set_request_headers == {"X-Real-IP": "127.0.0.1"}
    assert cfg.remove_request_headers == ["Cookie"]
    assert cfg.set_response_headers == {"X-Powered-By": "patchwork"}
    assert cfg.remove_response_headers == ["Server"]


def test_transform_config_partial_from_dict():
    cfg = TransformConfig.from_dict({"set_request_headers": {"X-Foo": "bar"}})
    assert cfg.set_request_headers == {"X-Foo": "bar"}
    assert cfg.remove_request_headers == []


def test_transform_config_invalid_set_request_headers():
    with pytest.raises(TypeError):
        TransformConfig(set_request_headers=["bad"])


def test_transform_config_invalid_remove_request_headers():
    with pytest.raises(TypeError):
        TransformConfig(remove_request_headers="bad")


# ---------------------------------------------------------------------------
# apply_request_transforms
# ---------------------------------------------------------------------------

def test_request_set_header_adds_new():
    cfg = TransformConfig(set_request_headers={"X-Custom": "hello"})
    result = apply_request_transforms({"Accept": "*/*"}, cfg)
    assert result["X-Custom"] == "hello"
    assert result["Accept"] == "*/*"


def test_request_set_header_overwrites_existing():
    cfg = TransformConfig(set_request_headers={"Authorization": "Bearer new"})
    result = apply_request_transforms({"Authorization": "Bearer old"}, cfg)
    assert result["Authorization"] == "Bearer new"


def test_request_remove_header():
    cfg = TransformConfig(remove_request_headers=["Cookie"])
    result = apply_request_transforms({"Cookie": "session=abc", "Accept": "*/*"}, cfg)
    assert "Cookie" not in result
    assert result["Accept"] == "*/*"


def test_request_remove_header_not_present_is_noop():
    """Removing a header that doesn't exist should not raise and leave headers intact."""
    cfg = TransformConfig(remove_request_headers=["X-Nonexistent"])
    result = apply_request_transforms({"Accept": "*/*"}, cfg)
    assert result == {"Accept": "*/*"}


def test_request_transform_does_not_mutate_original():
    original = {"X-Keep": "yes"}
    cfg = TransformConfig(set_request_headers={"X-Add": "new"})
    apply_request_transforms(original, cfg)
    assert "X-Add" not in original


# ---------------------------------------------------------------------------
# apply_response_transforms
# -----------------------------
