"""Combine findings into per-dimension scores and an overall benchmark.

Each dimension starts at 100 and loses points per finding by severity (capped at 0).
The artifact overall is the config-weighted mean of its dimension scores; the run
overall is the mean across artifacts.
"""

from __future__ import annotations

from ..config import Config
from ..model import (
    Artifact,
    ArtifactReview,
    ArtifactType,
    Dimension,
    DimensionScore,
    Finding,
    ReviewResult,
    Source,
)

ALL_DIMENSIONS = list(Dimension)

# Synthetic review path for findings that name no discovered artifact (e.g. a judge
# reporting "the specification"). They must stay visible in scores and reports.
UNATTRIBUTED_PATH = "(unattributed)"

# Judge findings legitimately vary run to run (#51), while lint findings do not.
# To keep a --fail-under gate from flapping on judge noise, judge findings are
# scored at half the deterministic lint penalty and a single judge finding is
# capped at 12 points (the lint "high" step) — one borderline judge call can move
# the score by at most a few points, and a judge "critical" can never swing 25
# points on its own. Lint findings keep full weight: they are reproducible.
JUDGE_PENALTY_SCALE = 0.5
JUDGE_PENALTY_CAP = 12.0


def finding_penalty(f: Finding) -> float:
    """Points a finding subtracts before dimension weighting (judge weight is capped)."""
    if f.source is Source.JUDGE:
        return min(f.severity.penalty * JUDGE_PENALTY_SCALE, JUDGE_PENALTY_CAP)
    return f.severity.penalty


def dedup_judge_findings(
    lint_findings: list[Finding], judge_findings: list[Finding]
) -> list[Finding]:
    """Judge findings minus those already covered by a lint finding (#43).

    method="both" pitfalls are detected deterministically by lint; a judge finding
    with the same (pitfall_id, artifact_path) is the same defect seen twice, and
    scoring both would systematically penalise hybrid runs vs rules-only runs for
    identical artifacts. Lint wins: it is reproducible.
    """
    lint_keys: set[tuple[str | None, str | None]] = {
        (f.pitfall_id, f.artifact_path) for f in lint_findings
    }
    return [
        f for f in judge_findings if (f.pitfall_id, f.artifact_path) not in lint_keys
    ]


def _dimension_scores(art_findings: list[Finding], config: Config) -> list[DimensionScore]:
    dim_scores: list[DimensionScore] = []
    for dim in ALL_DIMENSIONS:
        dim_findings = [f for f in art_findings if f.dimension == dim]
        weight = config.weight(dim)
        penalty = sum(finding_penalty(f) for f in dim_findings) * weight
        dim_scores.append(
            DimensionScore(
                dimension=dim,
                score=max(0.0, 100.0 - penalty),
                weight=weight,
                penalty=penalty,
                findings=dim_findings,
            )
        )
    return dim_scores


def score(
    artifacts: list[Artifact],
    findings: list[Finding],
    config: Config,
    engine: str = "rules",
) -> ReviewResult:
    by_path: dict[str, list[Finding]] = {}
    for f in findings:
        by_path.setdefault(f.artifact_path or "", []).append(f)

    reviews: list[ArtifactReview] = []
    for art in artifacts:
        reviews.append(
            ArtifactReview(
                path=art.path,
                type=art.type,
                feature_id=art.feature_id,
                dimension_scores=_dimension_scores(by_path.pop(art.path, []), config),
            )
        )

    # Findings whose artifact_path matched no artifact: bucket them under a
    # synthetic review so they still hit all_findings, reports, and the overall
    # score instead of silently vanishing.
    leftover = [f for fs in by_path.values() for f in fs]
    if leftover:
        reviews.append(
            ArtifactReview(
                path=UNATTRIBUTED_PATH,
                type=ArtifactType.UNKNOWN,
                feature_id=None,
                dimension_scores=_dimension_scores(leftover, config),
            )
        )

    return ReviewResult(artifacts=reviews, tool=config.tool, engine=engine)
