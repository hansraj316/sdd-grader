"""Regenerate the terminal screenshots embedded in README.md and docs/index.html.

Drives the real banner / wizard panels / review renderer with a recording rich
Console and exports docs/assets/*.svg, so the images always match the shipped
output. Run after any UX change:  uv run python scripts/screenshots.py
"""

from __future__ import annotations

from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "docs" / "assets"


def _console(width: int = 88) -> Console:
    return Console(record=True, width=width, force_terminal=True, highlight=False)


def _save(console: Console, name: str, title: str) -> None:
    ASSETS.mkdir(parents=True, exist_ok=True)
    out = ASSETS / name
    console.save_svg(str(out), title=title)
    print(f"wrote {out.relative_to(ROOT)}")


def shot_init() -> None:
    """Banner + agent selection + setup + next steps, as `sddgrade init` shows them."""
    from sddgrade.banner import show_banner
    from sddgrade.interactive import AGENT_CHOICES

    console = _console()
    show_banner(console)

    # The arrow-key selection panel, exactly as select_with_arrows() draws it
    # (frozen on the default choice; Live can't run against a recording console).
    keys = list(AGENT_CHOICES)
    grid = Table.grid(padding=(0, 2))
    grid.add_column(style="cyan", justify="left", width=3)
    grid.add_column(style="white", justify="left")
    for i, key in enumerate(keys):
        marker = "▶" if i == 0 else " "
        grid.add_row(marker, f"[cyan]{key}[/] [dim]({AGENT_CHOICES[key]})[/]")
    grid.add_row("", "")
    grid.add_row("", "[dim]Use ↑/↓ to navigate, Enter to select, Esc to cancel[/dim]")
    console.print()
    console.print(
        Panel(grid, title="[bold]Choose your agent integration:[/]",
              border_style="cyan", padding=(1, 2))
    )

    setup = [
        "[cyan]sddgrade project setup[/]",
        "",
        f"{'Path':<12} [dim]~/projects/my-app[/]",
        f"{'Integration':<12} [green]claude[/] [dim]({AGENT_CHOICES['claude']})[/]",
        f"{'Toolchain':<12} speckit [dim](detected)[/]",
    ]
    console.print(Panel("\n".join(setup), border_style="cyan", padding=(1, 2)))
    console.print("[green]✓[/] Initialized sddgrade. Wrote:")
    for p in (
        ".claude/commands/sddgrade.judge.md",
        ".claude/commands/sddgrade.review.md",
        ".claude/commands/sddgrade.fix.md",
        ".claude/commands/sddgrade.advise.md",
        ".claude/skills/sddgrade/SKILL.md",
        ".sddgrade.toml",
    ):
        console.print(f"  [dim]{p}[/]")
    steps = (
        "1. Open [cyan]Claude Code[/] in this project and run [cyan]/sddgrade.judge[/] — your agent\n"
        "   judges the specs and writes [dim].sddgrade/judge.json[/]\n"
        "2. Run [cyan]sddgrade review[/] — grades every artifact (lint + that judgment)\n"
        "3. Run [cyan]/sddgrade.fix[/] in your agent to apply the top fixes, then repeat 1-2 until clean\n"
        "4. Optional: gate CI with [cyan]sddgrade review --rules --fail-under 70[/]"
    )
    console.print(Panel(steps, title="Next Steps", border_style="cyan", padding=(1, 2)))
    _save(console, "init.svg", "sddgrade init")


def shot_review() -> None:
    """The real review renderer over the bundled bad fixture (lint-only)."""
    from sddgrade import config as config_mod
    from sddgrade.discovery import discover_artifacts, get_adapter
    from sddgrade.engine import lint as lint_mod
    from sddgrade.engine import scoring
    from sddgrade.report import terminal as terminal_report

    repo = ROOT / "tests" / "fixtures" / "speckit_bad"
    adapter = get_adapter("speckit")
    arts = discover_artifacts(repo)
    findings = lint_mod.lint(arts, adapter, repo)
    result = scoring.score(arts, findings, config_mod.Config(), engine="rules")

    console = _console(100)
    terminal_report.render(result, fail_under=70.0, console=console, top_fixes=0)
    _save(console, "review.svg", "sddgrade review")


if __name__ == "__main__":
    shot_init()
    shot_review()
