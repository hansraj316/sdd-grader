"""Structured machine-applicable fix data on findings (#63) and model cleanup (#65)."""

from __future__ import annotations

import json
from pathlib import Path

from sddgrade import config as config_mod
from sddgrade import model as model_mod
from sddgrade.discovery import discover_artifacts, get_adapter
from sddgrade.engine import lint as lint_mod
from sddgrade.engine import scoring
from sddgrade.model import (
    Artifact,
    ArtifactType,
    Dimension,
    Finding,
    ReviewResult,
    Severity,
    Source,
)
from sddgrade.report import json_out


def _lint(repo: Path):
    cfg = config_mod.Config()
    adapter = get_adapter(cfg.tool)
    arts = discover_artifacts(repo)
    return arts, lint_mod.lint(arts, adapter, repo)


def _enriched(repo: Path):
    arts, findings = _lint(repo)
    model_mod.enrich_structured_fixes(findings, arts)
    return arts, findings


# --------------------------------------------------------------------------- enrichment

def test_unresolved_marker_gets_resolve_marker_fix(bad_repo: Path):
    _, findings = _enriched(bad_repo)
    markers = [f for f in findings if f.pitfall_id == "SPEC-UNRESOLVED-CLARIFICATION"]
    assert markers
    for f in markers:
        assert f.fix_kind == "resolve-marker"
        assert f.fix_line_start is not None and f.fix_line_end is not None
        assert f.fix_line_start <= f.fix_line_end
        assert f.replacement_hint
    # The spec fixture's marker is on a known line.
    spec = next(f for f in markers if f.artifact_path.endswith("spec.md"))
    assert f"[NEEDS CLARIFICATION" in Path(spec.artifact_path).read_text().splitlines()[
        spec.fix_line_start - 1
    ]


def test_missing_section_gets_insert_section_fix(bad_repo: Path):
    _, findings = _enriched(bad_repo)
    missing = [f for f in findings if f.message.startswith("Missing required section")]
    assert missing
    for f in missing:
        assert f.fix_kind == "insert-section"
        assert f.replacement_hint and f.replacement_hint.startswith("## ")
        # The hint names the section from the message.
        assert f.replacement_hint[3:] in f.message


def test_prose_only_findings_have_no_structured_fix(bad_repo: Path):
    _, findings = _enriched(bad_repo)
    prose = [f for f in findings if f.pitfall_id == "SPEC-AMBIGUOUS-WORDING"]
    assert prose
    for f in prose:
        assert f.fix_kind is None
        assert f.fix_line_start is None and f.fix_line_end is None
        assert f.replacement_hint is None


def test_enrich_is_safe_without_matching_artifact():
    f = Finding(
        dimension=Dimension.CLARITY,
        severity=Severity.MEDIUM,
        message="1 unresolved [NEEDS CLARIFICATION] marker(s).",
        suggestion="resolve it",
        source=Source.JUDGE,
        pitfall_id="SPEC-UNRESOLVED-CLARIFICATION",
        artifact_path=None,
    )
    model_mod.enrich_structured_fixes([f], [])
    assert f.fix_kind is None  # no artifact text to derive a span from


def test_enrich_does_not_overwrite_existing_fix():
    art = Artifact(path="spec.md", type=ArtifactType.SPEC, raw="[NEEDS CLARIFICATION: x]")
    f = Finding(
        dimension=Dimension.CLARITY,
        severity=Severity.MEDIUM,
        message="1 unresolved [NEEDS CLARIFICATION] marker(s).",
        suggestion="resolve it",
        pitfall_id="SPEC-UNRESOLVED-CLARIFICATION",
        artifact_path="spec.md",
        fix_kind="replace-line",
        fix_line_start=9,
    )
    model_mod.enrich_structured_fixes([f], [art])
    assert f.fix_kind == "replace-line" and f.fix_line_start == 9


# --------------------------------------------------------------------------- JSON surface

def test_json_output_surfaces_fix_data(bad_repo: Path):
    arts, findings = _enriched(bad_repo)
    result = scoring.score(arts, findings, config_mod.Config())
    parsed = json.loads(json_out.render(result))
    all_findings = [
        f
        for a in parsed["artifacts"]
        for ds in a["dimension_scores"]
        for f in ds["findings"]
    ]
    assert all_findings and all("fix" in f for f in all_findings)
    fixes = [f["fix"] for f in all_findings if f["fix"] is not None]
    kinds = {fx["kind"] for fx in fixes}
    assert "resolve-marker" in kinds and "insert-section" in kinds
    marker = next(fx for fx in fixes if fx["kind"] == "resolve-marker")
    assert set(marker) == {"kind", "line_start", "line_end", "replacement_hint"}
    assert marker["line_start"] >= 1


def test_runner_wires_enrichment_into_json(bad_repo: Path, capsys):
    from sddgrade.runner import run_review

    run_review(bad_repo, backend="rules", json_out=True, write_markdown=False)
    parsed = json.loads(capsys.readouterr().out)
    fixes = [
        f["fix"]
        for a in parsed["artifacts"]
        for ds in a["dimension_scores"]
        for f in ds["findings"]
        if f.get("fix")
    ]
    assert any(fx["kind"] == "resolve-marker" for fx in fixes)


# --------------------------------------------------------------------------- #65: model defaults

def test_default_review_result_is_rules_only():
    r = ReviewResult()
    assert r.engine == "rules"
    assert r.judge_used is False
    assert r.coverage == "lint-only"


def test_hybrid_is_not_a_recognized_engine():
    # 'hybrid' was an unreachable phantom state; it must not claim judge coverage.
    assert ReviewResult(engine="hybrid").judge_used is False
