"""Engine-mode confidence / coverage transparency (issues #15, #16)."""

from __future__ import annotations

import io
import json
from pathlib import Path

from rich.console import Console

from sddreview import config as config_mod
from sddreview.discovery import discover_artifacts, get_adapter
from sddreview.engine import lint as lint_mod
from sddreview.engine import scoring
from sddreview.report import markdown
from sddreview.report.json_out import render as render_json
from sddreview.runner import EXIT_JUDGE_REQUIRED, run_review


def _quiet() -> Console:
    return Console(file=io.StringIO())


def _score(repo: Path, engine: str):
    cfg = config_mod.Config()
    adapter = get_adapter(cfg.tool)
    arts = discover_artifacts(repo)
    findings = lint_mod.lint(arts, adapter, repo)
    return scoring.score(arts, findings, cfg, engine=engine)


def test_rules_only_is_labeled_lint_only(good_repo: Path):
    result = _score(good_repo, "rules")
    assert result.coverage == "lint-only"
    assert result.judge_used is False
    assert "NOT" in result.coverage_note  # warns it's not full validation


def test_judge_backed_is_labeled_semantic(good_repo: Path):
    result = _score(good_repo, "agent")
    assert result.coverage == "lint+semantic"
    assert result.judge_used is True


def test_json_exposes_coverage(good_repo: Path):
    data = json.loads(render_json(_score(good_repo, "rules")))
    assert data["coverage"] == "lint-only"
    assert data["judge_used"] is False
    assert "coverage_note" in data


def test_markdown_explains_coverage(good_repo: Path):
    md = markdown.render(_score(good_repo, "rules"))
    assert "What this score proves" in md
    assert "lint-only" in md


def test_require_judge_fails_when_judge_unavailable(good_repo: Path):
    # No .sddreview/judge.json → agent judge degrades; --require-judge must fail (3).
    code = run_review(
        good_repo, backend="agent", require_judge=True, console=_quiet()
    )
    assert code == EXIT_JUDGE_REQUIRED


def test_require_judge_ok_with_stub_judgment(good_repo: Path):
    (good_repo / ".sddreview").mkdir(parents=True, exist_ok=True)
    (good_repo / ".sddreview" / "judge.json").write_text(json.dumps({"findings": []}))
    code = run_review(
        good_repo, backend="agent", require_judge=True, fail_under=70, console=_quiet()
    )
    assert code == 0
