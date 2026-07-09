"""Regression tests for issues #31 and #46.

#31: CLI --tool default must not override .sddgrade.toml.
#46: Unused config keys (integration, rubric_override) must be removed; scaffolded
     .sddgrade.toml must use tool = "auto" and not emit the integration key.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from sddgrade import config as config_mod
from sddgrade.runner import run_review

FIXTURES = Path(__file__).parent / "fixtures"


# ----------------------------------------------------------------- unit tests


def test_config_default_tool_is_auto():
    """Config.tool now defaults to 'auto', not 'speckit'."""
    cfg = config_mod.Config()
    assert cfg.tool == "auto"


def test_run_review_no_tool_kwarg_respects_config_file(tmp_path: Path):
    """run_review(tool=None) must honour .sddgrade.toml tool = 'openspec'."""
    import io
    import sys

    dst = tmp_path / "repo"
    shutil.copytree(FIXTURES / "openspec_good", dst)
    (dst / ".sddgrade.toml").write_text('[sddgrade]\ntool = "openspec"\n')

    buf = io.StringIO()
    old_stdout = sys.stdout
    sys.stdout = buf
    try:
        run_review(dst, backend="rules", json_out=True, tool=None)
    finally:
        sys.stdout = old_stdout

    data = json.loads(buf.getvalue())
    assert data.get("tool") == "openspec", (
        f"Expected tool='openspec' from config, got {data.get('tool')!r}"
    )


def test_explicit_tool_kwarg_overrides_config_file(tmp_path: Path):
    """run_review(tool='speckit') overrides .sddgrade.toml tool = 'openspec'."""
    import io
    import sys

    dst = tmp_path / "repo"
    shutil.copytree(FIXTURES / "speckit_good", dst)
    (dst / ".sddgrade.toml").write_text('[sddgrade]\ntool = "openspec"\n')

    buf = io.StringIO()
    old_stdout = sys.stdout
    sys.stdout = buf
    try:
        run_review(dst, backend="rules", json_out=True, tool="speckit")
    finally:
        sys.stdout = old_stdout

    data = json.loads(buf.getvalue())
    assert data.get("tool") == "speckit", (
        f"Expected explicit tool='speckit' to win, got {data.get('tool')!r}"
    )


# ----------------------------------------------------------------- CLI tests


def _cli(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "sddgrade.cli", *args],
        capture_output=True, text=True,
    )


def test_cli_no_tool_flag_respects_toml(tmp_path: Path):
    """CLI without --tool must honor .sddgrade.toml tool = 'openspec'."""
    dst = tmp_path / "repo"
    shutil.copytree(FIXTURES / "openspec_good", dst)
    (dst / ".sddgrade.toml").write_text('[sddgrade]\ntool = "openspec"\n')

    proc = _cli("review", str(dst), "--rules", "--json")
    assert proc.returncode in (0, 1), proc.stderr
    data = json.loads(proc.stdout)
    assert data.get("tool") == "openspec", (
        f"Expected tool='openspec' from config, got {data.get('tool')!r}"
    )


def test_cli_explicit_tool_flag_overrides_toml(tmp_path: Path):
    """CLI --tool speckit must override .sddgrade.toml tool = 'openspec'."""
    dst = tmp_path / "repo"
    shutil.copytree(FIXTURES / "speckit_good", dst)
    (dst / ".sddgrade.toml").write_text('[sddgrade]\ntool = "openspec"\n')

    proc = _cli("review", str(dst), "--rules", "--json", "--tool", "speckit")
    assert proc.returncode in (0, 1), proc.stderr
    data = json.loads(proc.stdout)
    assert data.get("tool") == "speckit", (
        f"Expected explicit --tool speckit to win, got {data.get('tool')!r}"
    )


# ----------------------------------------------------------------- issue #46 tests


def test_config_has_no_integration_field():
    """Config must not expose an .integration attribute (issue #46)."""
    cfg = config_mod.Config()
    assert not hasattr(cfg, "integration"), (
        "Config.integration was removed but is still present"
    )


def test_config_has_no_rubric_override_field():
    """Config must not expose a .rubric_override attribute (issue #46)."""
    cfg = config_mod.Config()
    assert not hasattr(cfg, "rubric_override"), (
        "Config.rubric_override was removed but is still present"
    )


def test_integration_key_in_toml_is_silently_ignored(tmp_path: Path):
    """A .sddgrade.toml that still has 'integration = ...' must not crash load()."""
    toml = tmp_path / ".sddgrade.toml"
    toml.write_text('[sddgrade]\nintegration = "claude"\nfail_under = 65\n')
    cfg = config_mod.load(tmp_path)
    assert cfg.fail_under == 65.0
    assert not hasattr(cfg, "integration")


def test_scaffolded_config_uses_auto_tool(tmp_path: Path):
    """sddgrade init must write tool = 'auto', not 'speckit' (issue #46)."""
    from sddgrade.integrations.agent import scaffold

    scaffold(tmp_path, "claude")
    toml_text = (tmp_path / ".sddgrade.toml").read_text()
    assert 'tool = "auto"' in toml_text, f"Expected tool = auto in scaffolded config:\n{toml_text}"
    assert 'tool = "speckit"' not in toml_text, (
        f"Scaffolded config must not force tool = 'speckit':\n{toml_text}"
    )


def test_scaffolded_config_has_no_integration_key(tmp_path: Path):
    """sddgrade init must not write an 'integration' key into .sddgrade.toml (issue #46)."""
    from sddgrade.integrations.agent import scaffold

    scaffold(tmp_path, "copilot")
    toml_text = (tmp_path / ".sddgrade.toml").read_text()
    assert "integration" not in toml_text, (
        f"Scaffolded config must not emit integration key:\n{toml_text}"
    )
