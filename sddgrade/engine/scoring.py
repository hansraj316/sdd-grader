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
)

ALL_DIMENSIONS = list(Dimension)

# Synthetic review path for findings that name no discovered artifact (e.g. a judge
# reporting "the specification"). They must stay visible in scores and reports.
UNATTRIBUTED_PATH = "(unattributed)"


def _dimension_scores(art_findings: list[Finding], config: Config) -> list[DimensionScore]:
    dim_scores: list[DimensionScore] = []
    for dim in ALL_DIMENSIONS:
        dim_findings = [f for f in art_findings if f.dimension == dim]
        weight = config.weight(dim)
        penalty = sum(f.severity.penalty for f in dim_findings) * weight
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
