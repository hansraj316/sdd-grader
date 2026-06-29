"""Locate and parse SDD artifacts under a repo, via the configured adapter.

`tool` may be an explicit adapter name (`speckit`, `openspec`) or `auto`, which picks
the adapter whose layout is actually present (preferring Spec-Kit when both match, to
preserve existing behavior).
"""

from __future__ import annotations

from pathlib import Path

from .adapters.base import ArtifactAdapter
from .adapters.openspec import OpenSpecAdapter
from .adapters.speckit import SpecKitAdapter
from .model import Artifact

_ADAPTERS: dict[str, type] = {
    "speckit": SpecKitAdapter,
    "openspec": OpenSpecAdapter,
}

# Order in which `auto` tries adapters. Spec-Kit first so existing repos are unaffected.
_AUTO_ORDER = ["speckit", "openspec"]


def get_adapter(tool: str = "speckit") -> ArtifactAdapter:
    """Return the adapter for an explicit toolchain name (defaults to Spec-Kit)."""
    cls = _ADAPTERS.get(tool, SpecKitAdapter)
    return cls()  # type: ignore[return-value]


def resolve_adapter(root: Path, tool: str = "speckit") -> ArtifactAdapter:
    """Resolve to a concrete adapter, honoring ``auto`` detection."""
    if tool == "auto":
        for name in _AUTO_ORDER:
            adapter = _ADAPTERS[name]()  # type: ignore[operator]
            if adapter.detect(root):
                return adapter  # type: ignore[return-value]
        return SpecKitAdapter()
    return get_adapter(tool)


def discover_artifacts(root: Path, tool: str = "speckit") -> list[Artifact]:
    """Find and parse every reviewable artifact under ``root``."""
    root = root.resolve()
    adapter = resolve_adapter(root, tool)
    return [adapter.parse(p, root) for p in adapter.discover(root)]
