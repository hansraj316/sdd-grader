"""CLI UX: banner suppression, guided init, and the summary-first terminal report."""

from __future__ import annotations

import io
import json
import re
import subprocess
import sys
from pathlib import Path

from rich.console import Console

from sddgrade import banner, config as config_mod, interactive
from sddgrade.discovery import discover_artifacts, get_adapter
from sddgrade.engine import lint as lint_mod
from sddgrade.engine import scoring
from sddgrade.report import terminal


def _cli(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "sddgrade.cli", *args],
        capture_output=True,
        text=True,
    )


# ------------------------------------------------------------------ banner contract

def test_banner_never_on_json_stdout(bad_repo: Path):
    proc = _cli("review", str(bad_repo), "--json")
    json.loads(proc.stdout)  # stdout must remain pure JSON
    assert "█" not in proc.stdout
    assert "█" not in proc.stderr


def test_banner_never_when_stdout_is_piped(bad_repo: Path):
    # Subprocess pipes are not TTYs: the human report renders, the banner doesn't.
    proc = _cli("review", str(bad_repo), "--rules")
    assert "█" not in proc.stdout
    assert "SDD Review" in proc.stdout  # report itself still present


def test_banner_never_on_piped_init(tmp_path: Path):
    proc = _cli("init", "--integration", "claude", str(tmp_path))
    assert proc.returncode == 0
    assert "█" not in proc.stdout


def test_show_banner_renders_art_and_tagline():
    buf = io.StringIO()
    banner.show_banner(Console(file=buf, force_terminal=True, width=100))
    out = buf.getvalue()
    assert "█" in out
    assert banner.TAGLINE in out  # "Grade specs like code"


def test_maybe_show_banner_requires_tty(monkeypatch):
    shown: list[bool] = []
    monkeypatch.setattr(banner, "show_banner", lambda console=None: shown.append(True))

    class FakeStdout:
        def isatty(self) -> bool:
            return False

    monkeypatch.setattr(banner.sys, "stdout", FakeStdout())
    assert banner.maybe_show_banner() is False
    assert shown == []

    class FakeTty:
        def isatty(self) -> bool:
            return True

    monkeypatch.setattr(banner.sys, "stdout", FakeTty())
    assert banner.maybe_show_banner() is True
    assert shown == [True]


# ------------------------------------------------------------------ guided init

def test_init_without_flag_non_tty_defaults_to_claude(tmp_path: Path):
    # No --integration and no TTY: prior behavior preserved (claude scaffold).
    proc = _cli("init", str(tmp_path))
    assert proc.returncode == 0
    assert (tmp_path / ".claude/commands/sddgrade.md").is_file()
    assert (tmp_path / ".sddgrade.toml").is_file()
    assert "defaulting to --integration claude" in proc.stderr


def test_init_wizard_scaffolds_selected_agent(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(interactive, "select_with_arrows", lambda *a, **k: "cursor")
    buf = io.StringIO()
    console = Console(file=buf, force_terminal=True, width=100)
    written = interactive.run_init_wizard(tmp_path, console=console)
    assert (tmp_path / ".cursor/commands/sddgrade.md").is_file()
    assert (tmp_path / ".sddgrade.toml").is_file()
    assert any(p.name == "sddgrade.md" for p in written)
    out = buf.getvalue()
    assert "Next Steps" in out
    assert "sddgrade review" in out
    assert "/sddgrade" in out  # tells the user to run the agent judge command


def test_init_wizard_reports_detected_toolchain(monkeypatch, good_repo: Path):
    monkeypatch.setattr(interactive, "select_with_arrows", lambda *a, **k: "claude")
    buf = io.StringIO()
    console = Console(file=buf, force_terminal=True, width=100)
    interactive.run_init_wizard(good_repo, console=console)
    assert "speckit" in buf.getvalue()  # the fixture layout is detected and named


def test_select_with_arrows_navigates_and_wraps(monkeypatch):
    # Scripted keys: down, down → third option; a second script wraps upward.
    def run(keys: list[str]) -> str:
        it = iter(keys)
        monkeypatch.setattr(interactive, "_get_key", lambda: next(it))
        buf = io.StringIO()
        return interactive.select_with_arrows(
            {"claude": "a", "copilot": "b", "cursor": "c"},
            "Choose:",
            "claude",
            console=Console(file=buf, force_terminal=True, width=80),
        )

    assert run(["down", "down", "enter"]) == "cursor"
    assert run(["up", "enter"]) == "cursor"  # wraps from first to last
    assert run(["enter"]) == "claude"  # default selection


def test_select_with_arrows_escape_cancels(monkeypatch):
    import pytest
    import typer as typer_mod

    monkeypatch.setattr(interactive, "_get_key", lambda: "escape")
    buf = io.StringIO()
    with pytest.raises(typer_mod.Exit) as excinfo:
        interactive.select_with_arrows(
            {"claude": "a"}, "Choose:", "claude",
            console=Console(file=buf, force_terminal=True, width=80),
        )
    assert excinfo.value.exit_code == 1


def test_numbered_fallback_selects_by_number(monkeypatch):
    monkeypatch.setattr(interactive.typer, "prompt", lambda *a, **k: "3")
    monkeypatch.setattr(interactive.typer, "echo", lambda *a, **k: None)
    picked = interactive._numbered_select(
        {"claude": "a", "copilot": "b", "cursor": "c"}, "Choose:", "claude"
    )
    assert picked == "cursor"


def test_wizard_agent_choices_match_supported_agents():
    from sddgrade.integrations.agent import supported_agents

    assert sorted(interactive.AGENT_CHOICES) == supported_agents()


# ------------------------------------------------------------------ report layout

_ANSI = re.compile(r"\x1b\[[0-9;]*m")


def _render(repo: Path, width: int = 200, top_fixes: int = 0) -> str:
    cfg = config_mod.Config()
    adapter = get_adapter("speckit")
    arts = discover_artifacts(repo)
    findings = lint_mod.lint(arts, adapter, repo)
    result = scoring.score(arts, findings, cfg)
    buf = io.StringIO()
    terminal.render(
        result, console=Console(file=buf, width=width), top_fixes=top_fixes
    )
    # Strip ANSI codes (FORCE_COLOR environments emit them even to StringIO) so
    # substring assertions test the text layout, not the styling.
    return _ANSI.sub("", buf.getvalue())


def test_summary_panel_renders_first(bad_repo: Path):
    out = _render(bad_repo)
    assert out.index("SDD Review") < out.index("Scores")
    assert out.index("Scores") < out.index("Next steps")
    assert "FAIL" in out and "gate 70" in out
    assert "coverage" in out and "lint-only" in out
    # The one-line verdict names where to start.
    assert "start with spec.md" in out


def test_scores_table_has_expected_cells(bad_repo: Path):
    out = _render(bad_repo)
    for header in ("Artifact", "Type", "Score /100", "Findings", "Worst severity"):
        assert header in out
    assert "spec.md" in out and "tasks.md" in out


def test_scores_table_sorted_worst_first(bad_repo: Path):
    cfg = config_mod.Config()
    arts = discover_artifacts(bad_repo)
    findings = lint_mod.lint(arts, get_adapter("speckit"), bad_repo)
    result = scoring.score(arts, findings, cfg)
    ordered = terminal._worst_first(result)
    scores = [a.overall for a in ordered]
    assert scores == sorted(scores)
    assert ordered[0].type.value == "spec"  # the defect-laden spec is worst


def test_findings_tables_have_expected_columns_and_fixes(bad_repo: Path):
    out = _render(bad_repo)
    for header in ("Severity", "Dimension", "Line", "Finding", "Fix"):
        assert header in out
    # Known lint content from the bad fixture survives into the table cells.
    assert "NEEDS" in out  # unresolved-clarification finding text
    assert "HIGH" in out or "CRITICAL" in out
    assert "completeness" in out or "clarity" in out


def test_top_fixes_preserved(bad_repo: Path):
    out = _render(bad_repo, top_fixes=3)
    assert "Top 3 fixes" in out
    assert "highest impact first" in out


def test_next_steps_contextual(bad_repo: Path, good_repo: Path):
    bad_out = _render(bad_repo)
    # lint-only + findings → suggests the agent judge and the HTML report.
    assert "/sddgrade" in bad_out
    assert "--html" in bad_out

    good_out = _render(good_repo)
    # clean → suggests the CI gate instead of fixes.
    assert "--fail-under" in good_out
