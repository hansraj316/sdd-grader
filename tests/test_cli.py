"""CLI contract tests: stream separation under --json and argument validation.

Run through a real subprocess so stdout/stderr are the actual process streams —
exactly what jq/CI parsers see (#40, #61).
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def _cli(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "sddgrade.cli", *args],
        capture_output=True,
        text=True,
    )


def test_json_stdout_is_pure_json_when_judge_unavailable(bad_repo: Path):
    # #40: default (agent) backend with no judge.json — the judge-unavailable
    # warning must go to stderr, leaving stdout parseable JSON.
    proc = _cli("review", str(bad_repo), "--json")
    data = json.loads(proc.stdout)
    assert "overall" in data and "artifacts" in data
    assert "Judge unavailable" in proc.stderr
    assert proc.returncode == 0  # #45: no gate requested → findings don't fail


def test_json_stdout_is_pure_json_with_require_judge(bad_repo: Path):
    # #40 (mirror path): the --require-judge ERROR must not trail the JSON on stdout.
    proc = _cli("review", str(bad_repo), "--json", "--require-judge")
    assert proc.returncode == 3
    data = json.loads(proc.stdout)
    assert "overall" in data
    assert "ERROR" in proc.stderr


def test_fail_under_flag_still_gates(bad_repo: Path):
    # #45: explicit --fail-under keeps its CI-gate behavior.
    proc = _cli("review", str(bad_repo), "--rules", "--json", "--fail-under", "70")
    assert proc.returncode == 1
    json.loads(proc.stdout)


def test_malformed_config_exits_nonzero_and_names_file(bad_repo: Path):
    # #47: bad TOML is a loud, named error — never silently discarded config.
    (bad_repo / ".sddgrade.toml").write_text("[sddgrade\nfail_under = 90\n")
    proc = _cli("review", str(bad_repo), "--rules")
    assert proc.returncode == 4
    assert ".sddgrade.toml" in proc.stderr
    assert proc.stdout == ""


def test_invalid_tool_is_rejected_with_choices(tmp_path: Path):
    # #61: --tool foo must error out listing the valid choices, not silently
    # fall back to the Spec-Kit adapter.
    proc = _cli("review", str(tmp_path), "--tool", "foo")
    assert proc.returncode == 2  # usage error
    assert proc.stdout == ""
    for choice in ("auto", "speckit", "openspec"):
        assert choice in proc.stderr
