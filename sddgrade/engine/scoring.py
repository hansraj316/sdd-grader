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
    Dimension,
    DimensionScore,
    Finding,
    ReviewResult,
)

ALL_DIMENSIONS = list(Dimension)


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
        art_findings = by_path.get(art.path, [])
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
        reviews.append(
            ArtifactReview(
                path=art.path,
                type=art.type,
                feature_id=art.feature_id,
                dimension_scores=dim_scores,
            )
        )

    return ReviewResult(artifacts=reviews, tool=config.tool, engine=engine)
