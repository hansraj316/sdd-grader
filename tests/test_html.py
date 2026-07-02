"""Self-contained HTML report."""

from __future__ import annotations

import io
from pathlib import Path

from rich.console import Console

from sddgrade import config as config_mod
from sddgrade.discovery import discover_artifacts, get_adapter
from sddgrade.engine import lint as lint_mod
from sddgrade.engine import scoring
from sddgrade.report import html
from sddgrade.runner import run_review


def _result(repo: Path):
    cfg = config_mod.Config()
    adapter = get_adapter(cfg.tool)
    arts = discover_artifacts(repo)
    findings = lint_mod.lint(arts, adapter, repo)
    return scoring.score(arts, findings, cfg)


def test_html_has_score_findings_and_fixes(bad_repo: Path):
    doc = html.render(_result(bad_repo))
    assert doc.startswith("<!doctype html>")
    assert "</html>" in doc
    assert "SDD Review Report" in doc
    # A real finding message and its fix suggestion appear.
    assert "unresolved [NEEDS CLARIFICATION]" in doc
    assert "Fix:" in doc
    assert "Top fixes" in doc
    # Coverage caveat is present.
    assert "lint-only" in doc


def test_html_escapes_content():
    # Angle brackets / ampersands in a finding must be escaped, not raw.
    from sddgrade.model import (
        ArtifactReview, ArtifactType, Dimension, DimensionScore, Finding,
        ReviewResult, Severity, Source,
    )
    f = Finding(dimension=Dimension.CLARITY, severity=Severity.HIGH,
                message="bad <script> & co", suggestion="use <safe> & sane",
                source=Source.LINT, artifact_path="spec.md")
    ds = DimensionScore(dimension=Dimension.CLARITY, score=80, penalty=12, findings=[f])
    ar = ArtifactReview(path="spec.md", type=ArtifactType.SPEC, feature_id="x",
                        dimension_scores=[ds])
    doc = html.render(ReviewResult(artifacts=[ar], engine="rules"))
    assert "<script>" not in doc
    assert "&lt;script&gt;" in doc


def test_html_clean_repo(good_repo: Path):
    doc = html.render(_result(good_repo))
    assert "No findings" in doc


def test_run_review_writes_html(bad_repo: Path, tmp_path: Path):
    out = tmp_path / "report.html"
    run_review(bad_repo, backend="rules", html_path=out,
               console=Console(file=io.StringIO()))
    assert out.is_file()
    assert "<!doctype html>" in out.read_text()
