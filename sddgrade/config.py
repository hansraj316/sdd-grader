"""Load and merge configuration: built-in defaults + user ``.sddgrade.toml``.

Everything has a sensible default so the common case (`sddgrade review`) needs no
config at all. A repo can override the toolchain, gate threshold, and dimension
weights in ``.sddgrade.toml`` at its root. Every key parsed here is honored by the
runner — a config key with no consumer must not be added (#46).
"""

from __future__ import annotations

import sys
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .model import Dimension

CONFIG_FILENAME = ".sddgrade.toml"


class ConfigError(Exception):
    """A config file the user wrote exists but cannot be read or parsed."""

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

    # Toolchain selection. "auto" detects the layout; a config-file `tool` wins over
    # auto-detection, and an explicit --tool flag wins over both (#31).
    tool: str = "auto"
    # CI gate threshold. None (the default) means no gating: a bare review exits 0
    # regardless of score. Opt in via --fail-under or `fail_under` in .sddgrade.toml.
    fail_under: float | None = None
    weights: dict[Dimension, float] = field(
        default_factory=lambda: dict(DEFAULT_WEIGHTS)
    )
    root: Path = field(default_factory=Path.cwd)

    def weight(self, dim: Dimension) -> float:
        return self.weights.get(dim, 1.0)


_KNOWN_KEYS: frozenset[str] = frozenset({"tool", "fail_under", "weights"})
_VALID_DIMENSIONS: frozenset[str] = frozenset(d.value for d in Dimension)


def _warn_unknown_keys(section: dict[str, Any], path: Path) -> None:
    """Emit stderr warnings for unrecognised keys in the config section."""
    for key in section:
        if key not in _KNOWN_KEYS:
            print(f"sddgrade: warning: unknown config key '{key}' in {path}", file=sys.stderr)
        elif key == "weights" and isinstance(section[key], dict):
            for wk in section[key]:
                if wk not in _VALID_DIMENSIONS:
                    print(
                        f"sddgrade: warning: unknown config key 'weights.{wk}' in {path}",
                        file=sys.stderr,
                    )


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

    # Config the user wrote must never be silently ignored: surface the problem
    # instead of quietly reverting their thresholds/weights to defaults.
    try:
        data = tomllib.loads(config_file.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as exc:
        raise ConfigError(f"invalid TOML in {config_file}: {exc}") from exc
    except OSError as exc:
        raise ConfigError(f"could not read {config_file}: {exc}") from exc

    section = data.get("sddgrade", data)
    _warn_unknown_keys(section, config_file)
    if isinstance(section.get("tool"), str):
        cfg.tool = section["tool"]
    if isinstance(section.get("fail_under"), (int, float)):
        cfg.fail_under = float(section["fail_under"])
    if isinstance(section.get("weights"), dict):
        cfg.weights = _coerce_weights(section["weights"])

    return cfg
