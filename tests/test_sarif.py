"""SARIF output (issue #14)."""

from __future__ import annotations

import json
from pathlib import Path

from sddgrade import config as config_mod
from sddgrade.discovery import discover_artifacts, get_adapter
from sddgrade.engine import lint as lint_mod
from sddgrade.engine import scoring
from sddgrade.report import sarif


def _result(repo: Path):
    cfg = config_mod.Config()
    adapter = get_adapter(cfg.tool)
    arts = discover_artifacts(repo)
    findings = lint_mod.lint(arts, adapter, repo)
    return scoring.score(arts, findings, cfg)


def test_sarif_is_valid_structure(bad_repo: Path):
    doc = json.loads(sarif.render(_result(bad_repo), root=bad_repo))
    assert doc["version"] == "2.1.0"
    run = doc["runs"][0]
    assert run["tool"]["driver"]["name"] == "sddgrade"
    assert run["tool"]["driver"]["rules"]
    assert run["results"]
    r = run["results"][0]
    assert {"ruleId", "level", "message", "locations"} <= set(r)
    assert r["level"] in {"error", "warning", "note"}
    # Pitfall ids become rule ids.
    rule_ids = {rule["id"] for rule in run["tool"]["driver"]["rules"]}
    assert any(rid.startswith("SPEC-") for rid in rule_ids)


def test_sarif_paths_are_relative(bad_repo: Path):
    doc = json.loads(sarif.render(_result(bad_repo), root=bad_repo))
    for res in doc["runs"][0]["results"]:
        uri = res["locations"][0]["physicalLocation"]["artifactLocation"]["uri"]
        assert not uri.startswith("/")  # relative to the repo root


def test_sarif_clean_repo_has_no_results(good_repo: Path):
    doc = json.loads(sarif.render(_result(good_repo), root=good_repo))
    assert doc["runs"][0]["results"] == []
