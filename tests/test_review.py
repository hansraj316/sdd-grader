"""End-to-end and unit tests for the deterministic review pipeline."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from rich.console import Console

from sddreview import config as config_mod
from sddreview.catalog import load_catalog
from sddreview.discovery import discover_artifacts, get_adapter
from sddreview.engine import lint as lint_mod
from sddreview.engine import scoring
from sddreview.model import ArtifactType
from sddreview.report import json_out, markdown
from sddreview.runner import run_review


# --------------------------------------------------------------------------- catalog

def test_catalog_loads_and_is_well_formed():
    cat = load_catalog()
    assert len(cat) >= 20
    assert len({p.id for p in cat.values()}) == len(cat)
    for p in cat.values():
        assert p.why and p.fix and p.detect
        assert p.method in {"lint", "judge", "both"}


# --------------------------------------------------------------------------- adapter

def test_adapter_detects_and_classifies(good_repo: Path):
    adapter = get_adapter("speckit")
    assert adapter.detect(good_repo)
    arts = discover_artifacts(good_repo)
    types = {a.type for a in arts}
    assert ArtifactType.SPEC in types
    assert ArtifactType.PLAN in types
    assert ArtifactType.TASKS in types
    assert ArtifactType.CONSTITUTION in types
    # Every artifact parsed into sections and tagged with its feature (except constitution).
    spec = next(a for a in arts if a.type == ArtifactType.SPEC)
    assert spec.feature_id == "001-task-export"
    assert spec.sections


def test_required_sections_fallback(good_repo: Path):
    adapter = get_adapter("speckit")
    req = adapter.required_sections(ArtifactType.PLAN, good_repo)
    assert "Constitution Check" in req


# --------------------------------------------------------------------------- lint

def _lint(repo: Path):
    adapter = get_adapter("speckit")
    arts = discover_artifacts(repo)
    return arts, lint_mod.lint(arts, adapter, repo)


def test_good_repo_is_clean(good_repo: Path):
    _arts, findings = _lint(good_repo)
    assert findings == [], [f.message for f in findings]


def test_bad_repo_trips_expected_pitfalls(bad_repo: Path):
    _arts, findings = _lint(bad_repo)
    ids = {f.pitfall_id for f in findings if f.pitfall_id}
    for expected in {
        "SPEC-UNRESOLVED-CLARIFICATION",
        "SPEC-LEFTOVER-PLACEHOLDER",
        "SPEC-AMBIGUOUS-WORDING",
        "SPEC-IMPL-DETAIL-LEAK",
        "PLAN-CONSTITUTION-UNCHECKED",
        "TASKS-TESTS-NOT-FIRST",
        "TASKS-MALFORMED",
        "CONST-PLACEHOLDER",
    }:
        assert expected in ids, f"expected {expected} in {sorted(ids)}"


def test_every_finding_has_a_suggestion(bad_repo: Path):
    _arts, findings = _lint(bad_repo)
    assert findings
    for f in findings:
        assert f.suggestion.strip(), f"empty suggestion for: {f.message}"


# --------------------------------------------------------------------------- scoring

def test_scoring_discriminates(good_repo: Path, bad_repo: Path):
    cfg = config_mod.Config()
    g_arts, g_find = _lint(good_repo)
    b_arts, b_find = _lint(bad_repo)
    good = scoring.score(g_arts, g_find, cfg)
    bad = scoring.score(b_arts, b_find, cfg)
    assert good.overall == 100.0
    assert bad.overall < 70.0
    # The defect-laden spec should be the worst artifact.
    worst = min(bad.artifacts, key=lambda a: a.overall)
    assert worst.type == ArtifactType.SPEC


# --------------------------------------------------------------------------- reports

def test_json_report_is_valid(bad_repo: Path):
    cfg = config_mod.Config()
    arts, find = _lint(bad_repo)
    result = scoring.score(arts, find, cfg)
    parsed = json.loads(json_out.render(result))
    assert "overall" in parsed and "artifacts" in parsed


def test_markdown_report_renders(bad_repo: Path):
    cfg = config_mod.Config()
    arts, find = _lint(bad_repo)
    md = markdown.render(scoring.score(arts, find, cfg))
    assert md.startswith("# SDD Review Report")
    assert "Fix:" in md


# --------------------------------------------------------------------------- runner / exit codes

def _quiet() -> Console:
    import io
    return Console(file=io.StringIO())


def test_run_review_exit_codes(good_repo: Path, bad_repo: Path):
    assert run_review(good_repo, backend="rules", fail_under=70, console=_quiet()) == 0
    assert run_review(bad_repo, backend="rules", fail_under=70, console=_quiet()) == 1


def test_run_review_no_artifacts(tmp_path: Path):
    assert run_review(tmp_path, backend="rules", console=_quiet()) == 2


def test_run_review_records_history(bad_repo: Path):
    run_review(bad_repo, backend="rules", fail_under=70, console=_quiet())
    hist = bad_repo / ".sddreview" / "history.jsonl"
    assert hist.is_file()
    line = json.loads(hist.read_text().splitlines()[0])
    assert line["overall"] < 70 and line["finding_count"] > 0


# --------------------------------------------------------------------------- json stdout cleanliness

def test_json_mode_stdout_is_valid_json_when_judge_unavailable(bad_repo: Path, capsys):
    """run_review --json must emit valid JSON on stdout even when no judge.json exists."""
    # No judge.json → agent backend degrades to rules-only; warning must not corrupt stdout.
    exit_code = run_review(bad_repo, backend="agent", json_out=True)
    out = capsys.readouterr().out
    parsed = json.loads(out)  # raises JSONDecodeError if warning bled onto stdout
    assert "overall" in parsed
    assert exit_code in (0, 1)


def test_json_mode_judge_warning_goes_to_stderr(bad_repo: Path, capsys):
    """The judge-unavailable warning must appear on stderr, not stdout, in --json mode."""
    run_review(bad_repo, backend="agent", json_out=True)
    captured = capsys.readouterr()
    # stdout must be a clean JSON document
    json.loads(captured.out)
    # the human warning lands on stderr
    assert "unavailable" in captured.err.lower()


# --------------------------------------------------------------------------- integrations

def test_init_scaffolds_agent_command(good_repo: Path):
    from sddreview.integrations import agent as agent_backend

    written = agent_backend.scaffold(good_repo, "claude")
    assert (good_repo / ".claude/commands/sddreview.md").is_file()
    assert (good_repo / ".sddreview.toml").is_file()
    assert any("sddreview.md" in str(p) for p in written)
    # The command embeds the pitfall guidance.
    text = (good_repo / ".claude/commands/sddreview.md").read_text()
    assert "PLAN-OVER-ENGINEERING" in text


def test_supported_agents_listed():
    from sddreview.integrations import agent as agent_backend

    agents = agent_backend.supported_agents()
    assert {"claude", "copilot", "cursor", "gemini"} <= set(agents)


def test_agent_backend_degrades_without_judgment(bad_repo: Path):
    # No judge.json present → agent backend degrades to rules-only, still exits 1.
    code = run_review(bad_repo, backend="agent", fail_under=70, console=_quiet())
    assert code == 1


def test_agent_judgment_merges(good_repo: Path):
    # A stub judgment adds a semantic finding; the good repo should then drop below 100.
    judge_dir = good_repo / ".sddreview"
    judge_dir.mkdir(parents=True, exist_ok=True)
    (judge_dir / "judge.json").write_text(json.dumps({
        "findings": [{
            "artifact": "plan.md",
            "dimension": "feasibility",
            "severity": "high",
            "message": "The synchronous design won't scale past 10k rows.",
            "suggestion": "Add a streaming/paginated export path.",
            "pitfall_id": "PLAN-OVER-ENGINEERING",
        }]
    }))
    # Use the lower-level judge to confirm merge without needing the agent.
    from sddreview.engine import judge as judge_mod

    arts = discover_artifacts(good_repo)
    raw = judge_mod.judge(arts, "agent", good_repo, config_mod.Config(), console=_quiet())
    assert len(raw) == 1
    assert raw[0].source.value == "judge"
    assert raw[0].pitfall_id == "PLAN-OVER-ENGINEERING"


# --------------------------------------------------------------------------- malformed judge.json (issue #30)

def test_agent_judge_top_level_list_does_not_crash(good_repo: Path):
    """Top-level JSON array in judge.json must not raise AttributeError."""
    judge_dir = good_repo / ".sddreview"
    judge_dir.mkdir(parents=True, exist_ok=True)
    (judge_dir / "judge.json").write_text(json.dumps(["not-an-object"]))
    from sddreview.engine import judge as judge_mod

    arts = discover_artifacts(good_repo)
    # Must degrade gracefully — the string item is skipped, returning zero findings.
    raw = judge_mod.judge(arts, "agent", good_repo, config_mod.Config(), console=_quiet())
    assert raw == []


def test_agent_judge_findings_list_with_non_dict_items(good_repo: Path):
    """String items in the findings array must be skipped, not crash."""
    judge_dir = good_repo / ".sddreview"
    judge_dir.mkdir(parents=True, exist_ok=True)
    (judge_dir / "judge.json").write_text(json.dumps({"findings": ["bad", 42, None]}))
    from sddreview.engine import judge as judge_mod

    arts = discover_artifacts(good_repo)
    raw = judge_mod.judge(arts, "agent", good_repo, config_mod.Config(), console=_quiet())
    assert raw == []


def test_agent_judge_malformed_degrades_in_review(good_repo: Path):
    """run_review must not raise on malformed judge.json; it degrades to rules-only."""
    judge_dir = good_repo / ".sddreview"
    judge_dir.mkdir(parents=True, exist_ok=True)
    (judge_dir / "judge.json").write_text(json.dumps(["not-an-object"]))
    # The top-level list is now accepted; items are skipped; review completes cleanly.
    exit_code = run_review(good_repo, backend="agent", console=_quiet())
    assert exit_code in (0, 1)


def test_agent_judge_scalar_top_level_raises_judge_unavailable(good_repo: Path):
    """A bare scalar (e.g. 42) at the top level of judge.json raises JudgeUnavailable."""
    judge_dir = good_repo / ".sddreview"
    judge_dir.mkdir(parents=True, exist_ok=True)
    (judge_dir / "judge.json").write_text("42")
    from sddreview.integrations.agent import AgentJudge
    from sddreview.engine.judge import JudgeUnavailable

    with pytest.raises(JudgeUnavailable, match="top level"):
        AgentJudge().read_judgment(good_repo)


# --------------------------------------------------------------------------- dashboard / advise

def test_sparkline_monotonic():
    from sddreview.dashboard import sparkline

    s = sparkline([0, 50, 100])
    assert len(s) == 3
    assert s[0] != s[-1]  # low and high render differently


def test_dashboard_runs_after_history(bad_repo: Path):
    from sddreview.dashboard import show

    run_review(bad_repo, backend="rules", console=_quiet())
    assert show(bad_repo, console=_quiet()) == 0


def test_advise_returns_recommendations(good_repo: Path):
    from sddreview.advisor import _recommendations, _scan

    info = _scan(good_repo)
    recs = _recommendations(info)
    assert len(recs) >= 4
    assert info["has_speckit"] is True
