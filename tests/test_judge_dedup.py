"""Tests for lint+judge deduplication of 'both'-method pitfalls.

Regression tests for issue #43: when a judge finding shares a (pitfall_id,
artifact_path) with a lint finding, the runner must include only the lint
finding (not both), so hybrid scores are comparable to rules-only scores for
identical artifacts.
"""

from __future__ import annotations

import io
import json
from pathlib import Path

import pytest
from rich.console import Console

from sddgrade.discovery import discover_artifacts
from sddgrade.engine import lint as lint_mod
from sddgrade.engine import scoring
from sddgrade.discovery import resolve_adapter
from sddgrade.integrations.agent import artifact_manifest
from sddgrade.model import Dimension, Severity, Source
from sddgrade.runner import run_review


def _write_judgment(root: Path, data: dict) -> None:
    judge_dir = root / ".sddgrade"
    judge_dir.mkdir(exist_ok=True)
    (judge_dir / "judge.json").write_text(json.dumps(data))


def test_duplicate_pitfall_suppressed(bad_repo: Path):
    """A judge finding with the same pitfall_id+artifact_path as a lint finding is dropped."""
    arts = discover_artifacts(bad_repo)
    adapter = resolve_adapter(bad_repo, "auto")
    lint_findings = lint_mod.lint(arts, adapter, bad_repo)

    # Pick a pitfall_id the lint layer already fires on this fixture.
    ambiguous_lints = [f for f in lint_findings if f.pitfall_id == "SPEC-AMBIGUOUS-WORDING"]
    assert ambiguous_lints, "fixture must trigger SPEC-AMBIGUOUS-WORDING"
    spec_path = ambiguous_lints[0].artifact_path
    assert spec_path is not None

    # Judge also fires the same pitfall on the same artifact (double-count scenario).
    _write_judgment(
        bad_repo,
        {
            "artifacts": artifact_manifest(arts, bad_repo),
            "findings": [
                {
                    "artifact": "specs/001-notifications/spec.md",
                    "dimension": "clarity",
                    "severity": "high",
                    "message": "Ambiguous wording detected by judge too.",
                    "suggestion": "Be precise.",
                    "pitfall_id": "SPEC-AMBIGUOUS-WORDING",
                }
            ],
        },
    )

    out = io.StringIO()
    run_review(bad_repo, backend="agent", console=Console(file=out))

    # Verify: only the lint's SPEC-AMBIGUOUS-WORDING finding survives.
    # We do that by re-running the engine manually and checking counts.
    final_judge_json = bad_repo / ".sddgrade" / "judge.json"
    raw = json.loads(final_judge_json.read_text())

    from sddgrade.engine.judge import to_findings
    judge_findings = to_findings(raw.get("findings", []), arts, bad_repo)
    merged = lint_findings + [
        f for f in judge_findings
        if (f.pitfall_id, f.artifact_path) not in {(g.pitfall_id, g.artifact_path) for g in lint_findings}
    ]
    ambiguous_merged = [f for f in merged if f.pitfall_id == "SPEC-AMBIGUOUS-WORDING"]
    assert len(ambiguous_merged) == len(ambiguous_lints), (
        "deduplicated merge must not add extra SPEC-AMBIGUOUS-WORDING findings"
    )


def test_novel_judge_finding_preserved(bad_repo: Path):
    """A judge finding with a pitfall_id not in lint findings is kept."""
    arts = discover_artifacts(bad_repo)
    adapter = resolve_adapter(bad_repo, "auto")
    lint_findings = lint_mod.lint(arts, adapter, bad_repo)

    # SPEC-NON-INDEPENDENT-STORY is method="judge" — lint never fires it.
    lint_ids = {f.pitfall_id for f in lint_findings}
    assert "SPEC-NON-INDEPENDENT-STORY" not in lint_ids, (
        "this pitfall must be judge-only for the test to be meaningful"
    )

    _write_judgment(
        bad_repo,
        {
            "artifacts": artifact_manifest(arts, bad_repo),
            "findings": [
                {
                    "artifact": "specs/001-notifications/spec.md",
                    "dimension": "clarity",
                    "severity": "medium",
                    "message": "Story depends on adjacent story.",
                    "suggestion": "Make it independent.",
                    "pitfall_id": "SPEC-NON-INDEPENDENT-STORY",
                }
            ],
        },
    )

    out = io.StringIO()
    run_review(bad_repo, backend="agent", console=Console(file=out))

    from sddgrade.engine.judge import to_findings
    raw = json.loads((bad_repo / ".sddgrade" / "judge.json").read_text())
    judge_findings = to_findings(raw.get("findings", []), arts, bad_repo)
    novel = [f for f in judge_findings if f.pitfall_id == "SPEC-NON-INDEPENDENT-STORY"]
    assert len(novel) == 1, "novel judge-only finding must not be dropped"


def test_dedup_does_not_lower_score_vs_rules_only(bad_repo: Path):
    """With dedup, agent score must be >= rules-only score for the same findings.

    Before the fix: a 'both'-method pitfall was penalised twice in hybrid mode,
    making the hybrid score lower than the rules-only score even without extra
    findings. After the fix the two must be equal when the judge adds no novel
    findings.
    """
    arts = discover_artifacts(bad_repo)
    adapter = resolve_adapter(bad_repo, "auto")
    lint_findings = lint_mod.lint(arts, adapter, bad_repo)

    from sddgrade.model import Finding
    # Judge echoes an existing lint pitfall (simulates method="both" double-count).
    dup_lint = lint_findings[0]
    _write_judgment(
        bad_repo,
        {
            "artifacts": artifact_manifest(arts, bad_repo),
            "findings": [
                {
                    "artifact": dup_lint.artifact_path.replace(str(bad_repo) + "/", "")
                    if dup_lint.artifact_path else "specs/001-notifications/spec.md",
                    "dimension": dup_lint.dimension.value,
                    "severity": dup_lint.severity.name.lower(),
                    "message": "Judge re-reports same pitfall.",
                    "suggestion": "Fix it.",
                    "pitfall_id": dup_lint.pitfall_id,
                }
            ],
        },
    )

    from sddgrade import config as config_mod
    cfg = config_mod.load(bad_repo)

    rules_score = scoring.score(arts, lint_findings, cfg, engine="rules").overall
    from sddgrade.engine.judge import to_findings
    raw = json.loads((bad_repo / ".sddgrade" / "judge.json").read_text())
    judge_findings = to_findings(raw.get("findings", []), arts, bad_repo)
    lint_keys = {(f.pitfall_id, f.artifact_path) for f in lint_findings}
    deduped = lint_findings + [f for f in judge_findings if (f.pitfall_id, f.artifact_path) not in lint_keys]
    deduped_score = scoring.score(arts, deduped, cfg, engine="agent").overall

    assert deduped_score >= rules_score, (
        f"deduped hybrid score ({deduped_score}) must not be lower than rules-only ({rules_score})"
    )


# ─── scoring.dedup_judge_findings (unit) ─────────────────────────────────────


def _finding(source: Source, pitfall_id: str | None, artifact_path: str):
    from sddgrade.model import Finding

    return Finding(
        dimension=Dimension.CLARITY,
        severity=Severity.MEDIUM,
        message="m",
        suggestion="s",
        source=source,
        pitfall_id=pitfall_id,
        artifact_path=artifact_path,
    )


def test_dedup_drops_judge_duplicate_same_pitfall_and_artifact():
    lint_f = _finding(Source.LINT, "SPEC-AMBIGUOUS-WORDING", "specs/a/spec.md")
    judge_dup = _finding(Source.JUDGE, "SPEC-AMBIGUOUS-WORDING", "specs/a/spec.md")
    assert scoring.dedup_judge_findings([lint_f], [judge_dup]) == []


def test_dedup_keeps_judge_finding_on_different_artifact():
    lint_f = _finding(Source.LINT, "SPEC-AMBIGUOUS-WORDING", "specs/a/spec.md")
    judge_f = _finding(Source.JUDGE, "SPEC-AMBIGUOUS-WORDING", "specs/b/spec.md")
    assert scoring.dedup_judge_findings([lint_f], [judge_f]) == [judge_f]


def test_dedup_keeps_judge_finding_with_different_pitfall():
    lint_f = _finding(Source.LINT, "SPEC-AMBIGUOUS-WORDING", "specs/a/spec.md")
    judge_f = _finding(Source.JUDGE, "SPEC-IMPLEMENTATION-DETAILS", "specs/a/spec.md")
    assert scoring.dedup_judge_findings([lint_f], [judge_f]) == [judge_f]


def test_dedup_keeps_judge_findings_without_pitfall_id():
    """pitfall-less judge findings never collide with pitfall-less lint findings
    on OTHER artifacts — only an exact (pitfall_id, artifact_path) pair drops."""
    lint_f = _finding(Source.LINT, None, "specs/a/spec.md")
    judge_f = _finding(Source.JUDGE, None, "specs/b/spec.md")
    assert scoring.dedup_judge_findings([lint_f], [judge_f]) == [judge_f]
