"""Response and request header transformation utilities."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class TransformConfig:
    """Configuration for header transformations applied to proxied requests/responses."""

    # Headers to add or overwrite on the upstream request
    set_request_headers: Dict[str, str] = field(default_factory=dict)
    # Headers to remove from the upstream request
    remove_request_headers: List[str] = field(default_factory=list)
    # Headers to add or overwrite on the downstream response
    set_response_headers: Dict[str, str] = field(default_factory=dict)
    # Headers to remove from the downstream response
    remove_response_headers: List[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not isinstance(self.set_request_headers, dict):
            raise TypeError("set_request_headers must be a dict")
        if not isinstance(self.remove_request_headers, list):
            raise TypeError("remove_request_headers must be a list")
        if not isinstance(self.set_response_headers, dict):
            raise TypeError("set_response_headers must be a dict")
        if not isinstance(self.remove_response_headers, list):
            raise TypeError("remove_response_headers must be a list")

    @classmethod
    def from_dict(cls, data: dict) -> "TransformConfig":
        return cls(
            set_request_headers=data.get("set_request_headers", {}),
            remove_request_headers=data.get("remove_request_headers", []),
            set_response_headers=data.get("set_response_headers", {}),
            remove_response_headers=data.get("remove_response_headers", []),
        )


def apply_request_transforms(
    headers: Dict[str, str], config: TransformConfig
) -> Dict[str, str]:
    """Return a new headers dict with request transforms applied."""
    result = dict(headers)
    for key in config.remove_request_headers:
        result.pop(key, None)
        # Also try canonical capitalisation variants
        result.pop(key.lower(), None)
        result.pop(key.title(), None)
    result.update(config.set_request_headers)
    return result


def apply_response_transforms(
    headers: Dict[str, str], config: TransformConfig
) -> Dict[str, str]:
    """Return a new headers dict with response transforms applied."""
    result = dict(headers)
    for key in config.remove_response_headers:
        result.pop(key, None)
        result.pop(key.lower(), None)
        result.pop(key.title(), None)
    result.update(config.set_response_headers)
    return result
