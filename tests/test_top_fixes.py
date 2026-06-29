"""Prioritized top-fixes mode (issue #19)."""

from __future__ import annotations

import json
from pathlib import Path

from sddreview import config as config_mod
from sddreview.discovery import discover_artifacts, get_adapter
from sddreview.engine import lint as lint_mod
from sddreview.engine import scoring
from sddreview.report.json_out import render as render_json


def _result(repo: Path):
    cfg = config_mod.Config()
    adapter = get_adapter(cfg.tool)
    arts = discover_artifacts(repo)
    findings = lint_mod.lint(arts, adapter, repo)
    return scoring.score(arts, findings, cfg)


def test_prioritized_is_impact_ordered(bad_repo: Path):
    result = _result(bad_repo)
    pri = result.prioritized_findings()
    assert pri
    impacts = [result.finding_impact(f) for f in pri]
    assert impacts == sorted(impacts, reverse=True)  # non-increasing impact
    # The top fix should be a high-severity finding on a high-weight artifact (the spec).
    assert impacts[0] >= impacts[-1]


def test_json_exposes_top_fixes(bad_repo: Path):
    data = json.loads(render_json(_result(bad_repo)))
    assert "top_fixes" in data
    assert 0 < len(data["top_fixes"]) <= 10
    first = data["top_fixes"][0]
    for key in ("severity", "message", "suggestion", "impact", "artifact_path"):
        assert key in first


def test_clean_repo_has_no_top_fixes(good_repo: Path):
    data = json.loads(render_json(_result(good_repo)))
    assert data["top_fixes"] == []
