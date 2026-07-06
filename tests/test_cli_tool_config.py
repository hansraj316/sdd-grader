"""Regression tests for issue #31: CLI --tool default must not override .sddgrade.toml.

When the user does not pass --tool, the config file's `tool` setting must be honored.
Only an explicit --tool flag on the command line should override config.
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
