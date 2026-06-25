"""Locate and parse SDD artifacts under a repo, via the configured adapter."""

from __future__ import annotations

from pathlib import Path

from .adapters.base import ArtifactAdapter
from .adapters.speckit import SpecKitAdapter
from .model import Artifact

_ADAPTERS: dict[str, type] = {
    "speckit": SpecKitAdapter,
}


def get_adapter(tool: str = "speckit") -> ArtifactAdapter:
    """Return the adapter for a toolchain name (defaults to Spec-Kit)."""
    cls = _ADAPTERS.get(tool, SpecKitAdapter)
    return cls()  # type: ignore[return-value]


def discover_artifacts(root: Path, tool: str = "speckit") -> list[Artifact]:
    """Find and parse every reviewable artifact under ``root``."""
    root = root.resolve()
    adapter = get_adapter(tool)
    return [adapter.parse(p, root) for p in adapter.discover(root)]
