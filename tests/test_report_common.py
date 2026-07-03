"""Shared report presentation helpers (#64) and integer score display (#59)."""

from __future__ import annotations

import io
import json

from rich.console import Console

from sddgrade.model import (
    ArtifactReview,
    ArtifactType,
    Dimension,
    DimensionScore,
    Finding,
    ReviewResult,
    Severity,
    Source,
)
from sddgrade.report import common, html, json_out, markdown, terminal


def _finding(sev: Severity, msg: str = "msg") -> Finding:
    return Finding(
        dimension=Dimension.CLARITY,
        severity=sev,
        message=msg,
        suggestion="fix it",
        source=Source.LINT,
        artifact_path="spec.md",
    )


def _fractional_result() -> ReviewResult:
    """A result whose overall is deliberately non-integer (73.4)."""
    ds = DimensionScore(
        dimension=Dimension.CLARITY,
        score=73.4,
        penalty=26.6,
        findings=[_finding(Severity.HIGH)],
    )
    ar = ArtifactReview(
        path="spec.md", type=ArtifactType.SPEC, feature_id="x", dimension_scores=[ds]
    )
    return ReviewResult(artifacts=[ar], engine="rules")


# --------------------------------------------------------------------------- helpers

def test_score_band_thresholds():
    assert common.score_band(69.9, 70.0) == "fail"
    assert common.score_band(70.0, 70.0) == "warn"
    assert common.score_band(84.9, 70.0) == "warn"
    assert common.score_band(85.0, 70.0) == "pass"
    # The gate is configurable; the warn threshold is the single shared constant.
    assert common.score_band(79.0, 80.0) == "fail"


def test_format_score_is_integer():
    assert common.format_score(73.4) == "73"
    assert common.format_score(73.6) == "74"
    assert common.format_score(100.0) == "100"


def test_pass_label():
    assert common.pass_label(70.0, 70.0) == "PASS"
    assert common.pass_label(69.9, 70.0) == "FAIL"


def test_sort_findings_severity_descending():
    fs = [_finding(Severity.INFO), _finding(Severity.CRITICAL), _finding(Severity.MEDIUM)]
    ordered = common.sort_findings(fs)
    assert [f.severity for f in ordered] == [
        Severity.CRITICAL, Severity.MEDIUM, Severity.INFO,
    ]


def test_severity_maps_cover_every_severity():
    for mapping in (common.SEV_ORDER, common.SEV_STYLE, common.SEV_COLOR, common.SARIF_LEVEL):
        assert set(mapping) == set(Severity)
    assert set(common.SARIF_LEVEL.values()) <= {"none", "note", "warning", "error"}


def test_top_fixes_default_count():
    ds = DimensionScore(
        dimension=Dimension.CLARITY,
        score=0,
        penalty=100,
        findings=[_finding(Severity.HIGH, f"m{i}") for i in range(8)],
    )
    ar = ArtifactReview(
        path="spec.md", type=ArtifactType.SPEC, feature_id="x", dimension_scores=[ds]
    )
    result = ReviewResult(artifacts=[ar], engine="rules")
    top = common.top_fixes(result)
    assert len(top) == common.DEFAULT_TOP_FIXES == 5
    assert top == result.prioritized_findings()[:5]


def test_finding_location():
    f = _finding(Severity.LOW)
    f.artifact_path = "/repo/specs/001/spec.md"
    f.line = 12
    assert common.finding_location(f) == "spec.md:12"
    f.line = None
    assert common.finding_location(f) == "spec.md"
    f.artifact_path = None
    assert common.finding_location(f) == "?"


# --------------------------------------------------------------------------- #59: integer display

def test_terminal_renders_integer_scores():
    result = _fractional_result()
    buf = io.StringIO()
    terminal.render(result, console=Console(file=buf, width=120), top_fixes=3)
    out = buf.getvalue()
    assert "73/100" in out
    assert "73.4" not in out


def test_markdown_renders_integer_scores():
    md = markdown.render(_fractional_result())
    assert "Overall score: 73/100" in md
    assert "73.4" not in md


def test_html_renders_integer_scores():
    doc = html.render(_fractional_result())
    assert ">73<" in doc
    assert "73.4" not in doc


def test_json_keeps_one_decimal_for_machines():
    parsed = json.loads(json_out.render(_fractional_result()))
    assert parsed["overall"] == 73.4
    assert parsed["artifacts"][0]["overall"] == 73.4
