"""Tests for judge attribution, output normalization, and judgment freshness.

Covers the three verified judge bugs: basename matching misattributing findings in
multi-feature repos (#36), the parser silently dropping findings on case/vocabulary
drift (#39), and stale .sddgrade/judge.json being trusted forever (#37).
"""

from __future__ import annotations

import io
import json
import shutil
from pathlib import Path

import pytest
from rich.console import Console

from sddgrade import config as config_mod
from sddgrade.discovery import discover_artifacts
from sddgrade.engine import judge as judge_mod
from sddgrade.engine import scoring
from sddgrade.engine.judge import JudgeUnavailable, build_prompt, to_findings
from sddgrade.engine.scoring import UNATTRIBUTED_PATH
from sddgrade.integrations.agent import AgentJudge, artifact_manifest
from sddgrade.model import Dimension, Severity
from sddgrade.runner import run_review


@pytest.fixture
def multi_repo(good_repo: Path) -> Path:
    """The good fixture with a second feature — every basename now collides."""
    shutil.copytree(
        good_repo / "specs" / "001-task-export",
        good_repo / "specs" / "002-task-import",
    )
    return good_repo


def _quiet() -> Console:
    return Console(file=io.StringIO())


def _item(**overrides) -> dict:
    base = {
        "artifact": "specs/001-task-export/spec.md",
        "dimension": "clarity",
        "severity": "high",
        "message": "Requirement FR-002 is ambiguous.",
        "suggestion": "State the exact export format.",
        "pitfall_id": None,
    }
    base.update(overrides)
    return base


# ----------------------------------------------------------------- #36 attribution

def test_prompt_labels_artifacts_with_relative_paths(multi_repo: Path):
    arts = discover_artifacts(multi_repo)
    prompt = build_prompt(arts, multi_repo)
    assert "----- specs/001-task-export/spec.md (spec) -----" in prompt
    assert "----- specs/002-task-import/spec.md (spec) -----" in prompt
    # No ambiguous bare-filename headers.
    assert "----- spec.md" not in prompt


def test_multi_feature_findings_attributed_to_right_feature(multi_repo: Path):
    arts = discover_artifacts(multi_repo)
    raw = [
        _item(artifact="specs/001-task-export/spec.md", message="001 defect"),
        _item(artifact="specs/002-task-import/spec.md", message="002 defect"),
    ]
    found = to_findings(raw, arts, multi_repo)
    assert len(found) == 2
    by_msg = {f.message: f.artifact_path for f in found}
    assert by_msg["001 defect"].endswith("specs/001-task-export/spec.md")
    assert by_msg["002 defect"].endswith("specs/002-task-import/spec.md")
    assert by_msg["001 defect"] != by_msg["002 defect"]


def test_unique_basename_still_resolves(good_repo: Path):
    # Single feature: a bare "plan.md" is unambiguous and maps to the full path.
    arts = discover_artifacts(good_repo)
    found = to_findings([_item(artifact="plan.md")], arts, good_repo)
    assert len(found) == 1
    assert found[0].artifact_path.endswith("specs/001-task-export/plan.md")


def test_ambiguous_basename_is_kept_not_guessed(multi_repo: Path, capsys):
    # Two features both have spec.md — a bare name must not be pinned to either.
    arts = discover_artifacts(multi_repo)
    found = to_findings([_item(artifact="spec.md")], arts, multi_repo)
    assert len(found) == 1
    assert found[0].artifact_path == "spec.md"  # kept, not resolved to a wrong feature
    assert "named no known artifact" in capsys.readouterr().err


def test_unresolved_finding_counts_in_score_and_reports(multi_repo: Path, capsys):
    # A judge finding naming no known artifact must still hit the score and reports.
    arts = discover_artifacts(multi_repo)
    raw = [_item(artifact="the specification", severity="critical")]
    findings = to_findings(raw, arts, multi_repo)
    assert len(findings) == 1
    assert "named no known artifact" in capsys.readouterr().err

    result = scoring.score(arts, findings, config_mod.Config(), engine="agent")
    assert result.overall < 100.0
    assert len(result.all_findings) == 1
    bucket = next(a for a in result.artifacts if a.path == UNATTRIBUTED_PATH)
    assert bucket.findings[0].message == "Requirement FR-002 is ambiguous."
    # And it survives into the serialized report.
    assert any(a["path"] == UNATTRIBUTED_PATH for a in result.to_dict()["artifacts"])


# ------------------------------------------------------------- #39 normalization

def test_case_insensitive_enum_parsing(good_repo: Path):
    arts = discover_artifacts(good_repo)
    found = to_findings(
        [_item(dimension="Clarity", severity="HIGH")], arts, good_repo
    )
    assert len(found) == 1
    assert found[0].dimension == Dimension.CLARITY
    assert found[0].severity == Severity.HIGH


def test_severity_and_dimension_synonyms_mapped(good_repo: Path):
    arts = discover_artifacts(good_repo)
    raw = [
        _item(severity="blocker", message="a"),
        _item(severity="major", message="b"),
        _item(severity="warning", message="c"),
        _item(dimension="ambiguity", message="d"),
    ]
    found = to_findings(raw, arts, good_repo)
    sev = {f.message: f.severity for f in found}
    assert sev["a"] == Severity.CRITICAL
    assert sev["b"] == Severity.HIGH
    assert sev["c"] == Severity.MEDIUM
    assert next(f for f in found if f.message == "d").dimension == Dimension.CLARITY


def test_unrecognized_enums_kept_with_defaults_and_warning(good_repo: Path, capsys):
    arts = discover_artifacts(good_repo)
    found = to_findings(
        [_item(dimension="vibes", severity="catastrophic")], arts, good_repo
    )
    assert len(found) == 1  # never silently dropped
    assert found[0].severity == Severity.MEDIUM
    assert found[0].dimension == Dimension.CLARITY
    assert "unrecognized dimension/severity" in capsys.readouterr().err


def test_messageless_items_skipped_with_warning(good_repo: Path, capsys):
    arts = discover_artifacts(good_repo)
    found = to_findings([_item(message="  "), "not even a dict"], arts, good_repo)
    assert found == []
    assert "had no message" in capsys.readouterr().err


# --------------------------------------------------------------- #37 staleness

def _write_judgment(root: Path, data: dict) -> None:
    judge_dir = root / ".sddgrade"
    judge_dir.mkdir(parents=True, exist_ok=True)
    (judge_dir / "judge.json").write_text(json.dumps(data))


def test_judgment_without_manifest_is_stale(good_repo: Path):
    arts = discover_artifacts(good_repo)
    _write_judgment(good_repo, {"findings": [_item()]})
    with pytest.raises(JudgeUnavailable, match="stale"):
        AgentJudge().read_judgment(good_repo, arts)


def test_judgment_with_mismatched_hash_is_stale(good_repo: Path):
    arts = discover_artifacts(good_repo)
    _write_judgment(
        good_repo,
        {"artifacts": artifact_manifest(arts, good_repo), "findings": [_item()]},
    )
    # Edit an artifact after the judgment was written.
    spec = good_repo / "specs" / "001-task-export" / "spec.md"
    spec.write_text(spec.read_text() + "\n\nNew requirement added after judging.\n")
    with pytest.raises(JudgeUnavailable, match="stale"):
        AgentJudge().read_judgment(good_repo, discover_artifacts(good_repo))


def test_judgment_missing_a_new_artifact_is_stale(good_repo: Path):
    arts = discover_artifacts(good_repo)
    _write_judgment(
        good_repo,
        {"artifacts": artifact_manifest(arts, good_repo), "findings": [_item()]},
    )
    # A whole new feature appears after the judgment was written.
    shutil.copytree(
        good_repo / "specs" / "001-task-export",
        good_repo / "specs" / "002-task-import",
    )
    with pytest.raises(JudgeUnavailable, match="stale"):
        AgentJudge().read_judgment(good_repo, discover_artifacts(good_repo))


def test_fresh_judgment_is_accepted(good_repo: Path):
    arts = discover_artifacts(good_repo)
    _write_judgment(
        good_repo,
        {"artifacts": artifact_manifest(arts, good_repo), "findings": [_item()]},
    )
    findings = AgentJudge().read_judgment(good_repo, arts)
    assert len(findings) == 1


def test_stale_judgment_degrades_to_rules_only(good_repo: Path):
    # End-to-end: a stale judge.json must not grade edited artifacts.
    arts = discover_artifacts(good_repo)
    _write_judgment(
        good_repo,
        {
            "artifacts": artifact_manifest(arts, good_repo),
            "findings": [_item(severity="critical")],
        },
    )
    spec = good_repo / "specs" / "001-task-export" / "spec.md"
    spec.write_text(spec.read_text() + "\n\nEdited after judging.\n")

    out = io.StringIO()
    code = run_review(good_repo, backend="agent", fail_under=70, console=Console(file=out))
    assert code == 0  # clean repo, rules-only — the stale critical finding is excluded
    assert "stale" in out.getvalue()

    # --require-judge refuses to pass on a stale judgment.
    assert (
        run_review(
            good_repo, backend="agent", fail_under=70, require_judge=True, console=_quiet()
        )
        == 3
    )


def test_fresh_judgment_survives_run_review(good_repo: Path):
    arts = discover_artifacts(good_repo)
    _write_judgment(
        good_repo,
        {
            "artifacts": artifact_manifest(arts, good_repo),
            "findings": [_item(severity="critical")],
        },
    )
    out = io.StringIO()
    code = run_review(
        good_repo, backend="agent", fail_under=70, require_judge=True,
        console=Console(file=out),
    )
    assert code == 0
    assert "lint+semantic" in out.getvalue()
