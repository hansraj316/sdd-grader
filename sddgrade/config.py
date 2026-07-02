"""Load and merge configuration: built-in defaults + user ``.sddgrade.toml``.

Everything has a sensible default so the common case (`sddgrade review`) needs no
config at all. A repo can override weights, thresholds, and the chosen agent in
``.sddgrade.toml`` at its root.
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .model import Dimension

CONFIG_FILENAME = ".sddgrade.toml"

# Default per-dimension penalty multipliers. Neutral (1.0) so a score reads as a
# plain penalty sum; bump a dimension in .sddgrade.toml to make its defects hurt more.
DEFAULT_WEIGHTS: dict[Dimension, float] = {
    Dimension.COMPLETENESS: 1.0,
    Dimension.CLARITY: 1.0,
    Dimension.TESTABILITY: 1.0,
    Dimension.TRACEABILITY: 1.0,
    Dimension.CONSISTENCY: 1.0,
    Dimension.FEASIBILITY: 1.0,
    Dimension.CONSTITUTIONAL: 1.0,
}


@dataclass
class Config:
    """Resolved configuration for a run."""

    tool: str = "speckit"
    integration: str = "claude"
    fail_under: float = 70.0
    weights: dict[Dimension, float] = field(
        default_factory=lambda: dict(DEFAULT_WEIGHTS)
    )
    # Optional path to a user rubric dir/file that overrides bundled rubrics.
    rubric_override: str | None = None
    root: Path = field(default_factory=Path.cwd)

    def weight(self, dim: Dimension) -> float:
        return self.weights.get(dim, 1.0)


def _coerce_weights(raw: dict[str, Any]) -> dict[Dimension, float]:
    out = dict(DEFAULT_WEIGHTS)
    for key, value in raw.items():
        try:
            out[Dimension(key)] = float(value)
        except (ValueError, TypeError):
            # Unknown dimension or non-numeric weight: ignore rather than crash.
            continue
    return out


def find_config_file(start: Path) -> Path | None:
    """Walk upward from ``start`` looking for a ``.sddgrade.toml``."""
    start = start.resolve()
    for parent in [start, *start.parents]:
        candidate = parent / CONFIG_FILENAME
        if candidate.is_file():
            return candidate
    return None


def load(root: Path | None = None) -> Config:
    """Build a :class:`Config`, merging any discovered ``.sddgrade.toml`` over defaults."""
    root = (root or Path.cwd()).resolve()
    cfg = Config(root=root)

    config_file = find_config_file(root)
    if config_file is None:
        return cfg

    try:
        data = tomllib.loads(config_file.read_text(encoding="utf-8"))
    except (tomllib.TOMLDecodeError, OSError):
        # A malformed config shouldn't break a review; fall back to defaults.
        return cfg

    section = data.get("sddgrade", data)
    if isinstance(section.get("tool"), str):
        cfg.tool = section["tool"]
    if isinstance(section.get("integration"), str):
        cfg.integration = section["integration"]
    if isinstance(section.get("fail_under"), (int, float)):
        cfg.fail_under = float(section["fail_under"])
    if isinstance(section.get("rubric_override"), str):
        cfg.rubric_override = section["rubric_override"]
    if isinstance(section.get("weights"), dict):
        cfg.weights = _coerce_weights(section["weights"])

    return cfg
