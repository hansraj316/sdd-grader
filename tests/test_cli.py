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


FIXTURES = Path(__file__).parent / "fixtures"


# ------------------------------------------------------------- tool precedence (#31)

def test_cli_without_tool_flag_honors_config(tmp_path: Path):
    # #31 regression, end to end: no --tool flag → the config file's `tool` wins
    # over auto's Spec-Kit preference in a mixed-layout repo.
    import shutil

    shutil.copytree(FIXTURES / "speckit_good", tmp_path, dirs_exist_ok=True)
    shutil.copytree(FIXTURES / "openspec_good", tmp_path, dirs_exist_ok=True)
    (tmp_path / ".sddgrade.toml").write_text('[sddgrade]\ntool = "openspec"\n')
    proc = _cli("review", str(tmp_path), "--rules", "--json")
    data = json.loads(proc.stdout)
    assert data["tool"] == "openspec"
    assert all("openspec" in a["path"] for a in data["artifacts"])


# ---------------------------------------------------------- removed commands (#62)

def test_removed_command_groups_are_gone():
    # `self check` duplicated --version, `self upgrade` didn't upgrade, and
    # `integration list` wrapped a constant. All were removed in #62.
    for args in (("self", "check"), ("self", "upgrade"), ("integration", "list")):
        proc = _cli(*args)
        assert proc.returncode != 0, f"{args} should no longer exist"
        assert "No such command" in proc.stderr

def test_version_flag_still_works():
    proc = _cli("--version")
    assert proc.returncode == 0
    assert proc.stdout.startswith("sddgrade ")


# ----------------------------------------------------------- init scaffolding (#46)

def test_init_scaffold_contains_only_honored_keys(tmp_path: Path):
    # Every key `init` writes must actually change review behavior (#46):
    # `integration` and `rubric_override` were parsed-but-ignored and are gone.
    import tomllib

    proc = _cli("init", "--integration", "claude", str(tmp_path))
    assert proc.returncode == 0
    data = tomllib.loads((tmp_path / ".sddgrade.toml").read_text())
    assert set(data) == {"sddgrade"}
    assert set(data["sddgrade"]) == {"tool", "fail_under"}
    assert data["sddgrade"]["tool"] == "auto"


def test_init_scaffold_round_trips_through_config_loader(tmp_path: Path):
    from sddgrade import config as config_mod

    proc = _cli("init", str(tmp_path))
    assert proc.returncode == 0
    cfg = config_mod.load(tmp_path)
    assert cfg.tool == "auto"
    assert cfg.fail_under == 70.0
    assert not hasattr(cfg, "integration")
    assert not hasattr(cfg, "rubric_override")


def test_init_rejects_unknown_integration_listing_supported(tmp_path: Path):
    # The old `integration list` command folded into init's error output (#62).
    from sddgrade.integrations.agent import supported_agents

    proc = _cli("init", "--integration", "nope", str(tmp_path))
    assert proc.returncode == 2
    for name in supported_agents():
        assert name in proc.stderr
    assert not (tmp_path / ".sddgrade.toml").exists()


def test_init_help_lists_supported_agents():
    from sddgrade.integrations.agent import supported_agents

    proc = _cli("init", "--help")
    assert proc.returncode == 0
    for name in supported_agents():
        assert name in proc.stdout
