"""Load the pitfall catalog (rubric/pitfalls.toml) into typed objects.

The catalog is bundled package data. Findings and history reference pitfalls by
``id`` so results stay reproducible. Lexical (`patterns`) checks are run generically
by the lint engine; structural and cross-artifact pitfalls have dedicated checks
keyed by ``id``; the full catalog is also handed to the judge as guidance.
"""

from __future__ import annotations

import re
import tomllib
from dataclasses import dataclass, field
from functools import lru_cache
from importlib import resources

from .model import ArtifactType, Dimension, Severity


@dataclass(frozen=True)
class Pitfall:
    id: str
    name: str
    dimension: Dimension
    artifacts: frozenset[ArtifactType]
    severity: Severity
    method: str  # "lint" | "judge" | "both"
    why: str
    detect: str
    fix: str
    patterns: tuple[str, ...] = ()
    compiled: tuple[re.Pattern[str], ...] = field(default=())

    def applies_to(self, atype: ArtifactType) -> bool:
        return atype in self.artifacts

    @property
    def lint_detectable(self) -> bool:
        return self.method in ("lint", "both")

    @property
    def judge_detectable(self) -> bool:
        return self.method in ("judge", "both")


def _coerce(entry: dict) -> Pitfall:
    artifacts = frozenset(
        ArtifactType(a) for a in entry.get("artifacts", []) if _is_artifact(a)
    )
    patterns = tuple(entry.get("patterns", []) or ())
    compiled = tuple(re.compile(p, re.IGNORECASE) for p in patterns)
    return Pitfall(
        id=entry["id"],
        name=entry["name"],
        dimension=Dimension(entry["dimension"]),
        artifacts=artifacts,
        severity=Severity(entry["severity"]),
        method=entry["method"],
        why=entry["why"],
        detect=entry["detect"],
        fix=entry["fix"],
        patterns=patterns,
        compiled=compiled,
    )


def _is_artifact(value: str) -> bool:
    try:
        ArtifactType(value)
        return True
    except ValueError:
        return False


@lru_cache(maxsize=1)
def load_catalog() -> dict[str, Pitfall]:
    """Return the bundled pitfall catalog keyed by id (cached)."""
    text = (resources.files("sddgrade.rubric") / "pitfalls.toml").read_text(
        encoding="utf-8"
    )
    data = tomllib.loads(text)
    return {e["id"]: _coerce(e) for e in data.get("pitfall", [])}
