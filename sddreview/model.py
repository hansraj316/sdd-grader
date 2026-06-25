"""Normalized data model shared across adapters, engine, reports, and history.

These types are the stable interface between layers. Adapters produce ``Artifact``
objects; the engine produces ``Finding`` / ``DimensionScore`` / ``ArtifactReview`` /
``ReviewResult``; reports and history only ever read these. Keeping them dependency
free (stdlib dataclasses + enums) makes the whole pipeline easy to unit-test.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class Dimension(str, Enum):
    """Quality dimensions an artifact is scored on (see plan: built-in rubric)."""

    COMPLETENESS = "completeness"
    CLARITY = "clarity"
    TESTABILITY = "testability"
    TRACEABILITY = "traceability"
    CONSISTENCY = "consistency"
    FEASIBILITY = "feasibility"
    CONSTITUTIONAL = "constitutional"


class Severity(str, Enum):
    """How much a finding should hurt the score and draw attention."""

    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

    @property
    def penalty(self) -> float:
        """Points deducted from the 100 baseline per occurrence.

        Tuned so a handful of real defects produces a clearly failing score while
        still leaving a usable gradient below it (several mediums don't instantly
        floor an artifact, but a few highs do drag it into fail territory).
        """
        return {
            Severity.INFO: 0.0,
            Severity.LOW: 2.0,
            Severity.MEDIUM: 6.0,
            Severity.HIGH: 12.0,
            Severity.CRITICAL: 25.0,
        }[self]


class ArtifactType(str, Enum):
    """The kinds of Spec-Kit artifacts the reviewer understands."""

    SPEC = "spec"
    PLAN = "plan"
    TASKS = "tasks"
    CONSTITUTION = "constitution"
    RESEARCH = "research"
    DATA_MODEL = "data-model"
    QUICKSTART = "quickstart"
    CONTRACT = "contract"
    CHECKLIST = "checklist"
    UNKNOWN = "unknown"

    @property
    def weight(self) -> float:
        """How much this artifact counts toward the run's overall score.

        The core SDD trio carries the most signal; supporting docs count less.
        """
        return {
            ArtifactType.SPEC: 1.5,
            ArtifactType.PLAN: 1.25,
            ArtifactType.TASKS: 1.25,
            ArtifactType.CONSTITUTION: 1.0,
        }.get(self, 0.5)


class Source(str, Enum):
    """Which half of the hybrid engine produced a finding."""

    LINT = "lint"
    JUDGE = "judge"


@dataclass(frozen=True)
class Section:
    """A heading and its body text within an artifact (for required-section checks)."""

    title: str
    level: int
    body: str
    line: int


@dataclass
class Artifact:
    """A parsed SDD artifact, normalized so the engine is adapter-agnostic.

    ``feature_id`` groups artifacts of one feature (Spec-Kit ``specs/<feature-id>/``);
    ``raw`` keeps the original text for regex/marker checks the structured view loses.
    """

    path: str
    type: ArtifactType
    feature_id: str | None = None
    raw: str = ""
    sections: list[Section] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def section(self, title_substr: str) -> Section | None:
        """First section whose title contains ``title_substr`` (case-insensitive)."""
        needle = title_substr.lower()
        for s in self.sections:
            if needle in s.title.lower():
                return s
        return None

    def has_section(self, title_substr: str) -> bool:
        return self.section(title_substr) is not None


@dataclass
class Finding:
    """A single issue, always paired with a concrete fix ``suggestion``.

    ``pitfall_id`` links the finding to an entry in the research-backed pitfall
    catalog (``rubric/pitfalls.toml``) when it matches a known anti-pattern.
    """

    dimension: Dimension
    severity: Severity
    message: str
    suggestion: str
    source: Source = Source.LINT
    pitfall_id: str | None = None
    artifact_path: str | None = None
    line: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "dimension": self.dimension.value,
            "severity": self.severity.value,
            "message": self.message,
            "suggestion": self.suggestion,
            "source": self.source.value,
            "pitfall_id": self.pitfall_id,
            "artifact_path": self.artifact_path,
            "line": self.line,
        }


@dataclass
class DimensionScore:
    """0-100 score for one dimension, plus the weighted penalty behind it.

    ``penalty`` is the weighted sum of finding penalties (already multiplied by the
    dimension weight); ``score`` is ``max(0, 100 - penalty)``. Keeping the penalty
    explicit lets the artifact overall be computed consistently from penalties
    rather than re-averaging scores (which dilutes when only a few dimensions fail).
    """

    dimension: Dimension
    score: float
    weight: float = 1.0
    penalty: float = 0.0
    findings: list[Finding] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "dimension": self.dimension.value,
            "score": round(self.score, 1),
            "weight": self.weight,
            "findings": [f.to_dict() for f in self.findings],
        }


@dataclass
class ArtifactReview:
    """The full review of one artifact: per-dimension scores + weighted overall."""

    path: str
    type: ArtifactType
    feature_id: str | None
    dimension_scores: list[DimensionScore] = field(default_factory=list)

    @property
    def findings(self) -> list[Finding]:
        out: list[Finding] = []
        for ds in self.dimension_scores:
            out.extend(ds.findings)
        return out

    @property
    def overall(self) -> float:
        """Penalty-based: 100 minus the total weighted penalty across all dimensions.

        Penalty-based (not an average of dimension scores) so that real defects
        actually lower the score instead of being diluted by dimensions that
        happen to have no findings.
        """
        total_penalty = sum(ds.penalty for ds in self.dimension_scores)
        return max(0.0, 100.0 - total_penalty)

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "type": self.type.value,
            "feature_id": self.feature_id,
            "overall": round(self.overall, 1),
            "dimension_scores": [ds.to_dict() for ds in self.dimension_scores],
        }


@dataclass
class ReviewResult:
    """The result of one ``sddreview review`` run over a repo."""

    artifacts: list[ArtifactReview] = field(default_factory=list)
    tool: str = "speckit"
    engine: str = "hybrid"
    timestamp: str | None = None  # ISO 8601; stamped by the caller, not at parse time

    @property
    def overall(self) -> float:
        """Artifact-type-weighted mean of artifact overalls (core trio counts most)."""
        if not self.artifacts:
            return 100.0
        total_w = sum(a.type.weight for a in self.artifacts) or 1.0
        return sum(a.overall * a.type.weight for a in self.artifacts) / total_w

    @property
    def all_findings(self) -> list[Finding]:
        out: list[Finding] = []
        for a in self.artifacts:
            out.extend(a.findings)
        return out

    def to_dict(self) -> dict[str, Any]:
        return {
            "tool": self.tool,
            "engine": self.engine,
            "timestamp": self.timestamp,
            "overall": round(self.overall, 1),
            "artifacts": [a.to_dict() for a in self.artifacts],
        }
