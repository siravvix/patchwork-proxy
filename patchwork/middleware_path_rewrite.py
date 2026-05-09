"""Middleware that rewrites request paths using regex substitution."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Tuple

from patchwork.middleware import MiddlewarePipeline, RequestContext


@dataclass
class PathRewriteRule:
    pattern: str
    replacement: str
    _compiled: re.Pattern = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if not self.pattern:
            raise ValueError("pattern must not be empty")
        try:
            self._compiled = re.compile(self.pattern)
        except re.error as exc:
            raise ValueError(f"invalid regex pattern {self.pattern!r}: {exc}") from exc

    def apply(self, path: str) -> str:
        return self._compiled.sub(self.replacement, path)

    def matches(self, path: str) -> bool:
        return bool(self._compiled.search(path))


@dataclass
class PathRewriteConfig:
    enabled: bool = False
    rules: List[PathRewriteRule] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.enabled and not self.rules:
            raise ValueError("path rewrite is enabled but no rules are defined")

    @classmethod
    def from_dict(cls, data: dict) -> "PathRewriteConfig":
        enabled = bool(data.get("enabled", False))
        raw_rules: List[dict] = data.get("rules", [])
        rules = [
            PathRewriteRule(pattern=r["pattern"], replacement=r.get("replacement", ""))
            for r in raw_rules
        ]
        return cls(enabled=enabled, rules=rules)


def make_path_rewrite_middleware(
    config: PathRewriteConfig,
) -> callable:
    """Return a pre-middleware function that rewrites ctx.path in-place."""

    def pre_middleware(ctx: RequestContext) -> None:
        if not config.enabled:
            return
        original = ctx.request.get("path", "/")
        rewritten = original
        for rule in config.rules:
            if rule.matches(rewritten):
                rewritten = rule.apply(rewritten)
                break  # first-match wins
        ctx.request["path"] = rewritten
        if rewritten != original:
            ctx.meta["path_rewritten"] = True
            ctx.meta["original_path"] = original

    return pre_middleware


def build_default_path_rewrite_middleware(
    pipeline: MiddlewarePipeline,
    config: PathRewriteConfig,
) -> None:
    """Register path-rewrite pre-middleware on *pipeline*."""
    pipeline.add_pre(make_path_rewrite_middleware(config))
