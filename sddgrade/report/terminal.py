"""Rich terminal report — the default human-facing output of `sddgrade review`."""

from __future__ import annotations

from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from ..model import Finding, ReviewResult
from . import common

_BAND_STYLE = {"fail": "bold red", "warn": "yellow", "pass": "green"}


def _score_style(score: float, fail_under: float) -> str:
    return _BAND_STYLE[common.score_band(score, fail_under)]


def _print_fix_line(console: Console, f: Finding, index: int) -> None:
    sev_style = common.SEV_STYLE.get(f.severity, "white")
    tag = f" [dim]{f.pitfall_id}[/]" if f.pitfall_id else ""
    console.print(
        f"  [bold]{index}.[/] [{sev_style}]{f.severity.value.upper()}[/] "
        f"[dim]{common.finding_location(f)}{tag}[/] {f.message}"
    )
    console.print(f"     [green]fix[/] {f.suggestion}")


def render(
    result: ReviewResult,
    fail_under: float = 70.0,
    console: Console | None = None,
    top_fixes: int = 0,
) -> None:
    console = console or Console()

    style = _score_style(result.overall, fail_under)
    console.print(
        Panel(
            f"[{style}]{common.format_score(result.overall)}/100[/]   "
            f"[dim]tool={result.tool} engine={result.engine} "
            f"artifacts={len(result.artifacts)} "
            f"findings={len(result.all_findings)}[/]",
            title="SDD Review — overall",
            expand=False,
        )
    )

    # Coverage banner — make engine-mode confidence explicit so a clean rules-only
    # score is never mistaken for full semantic validation.
    if result.judge_used:
        console.print(f"[green]coverage:[/] {result.coverage} — {result.coverage_note}")
    else:
        console.print(
            Panel(
                f"[yellow]{result.coverage_note}[/]",
                title="⚠ lint-only score",
                expand=False,
            )
        )

    # Per-artifact summary table.
    table = Table(show_lines=False, expand=True)
    table.add_column("Artifact", overflow="fold")
    table.add_column("Type", justify="left")
    table.add_column("Score", justify="right")
    table.add_column("Findings", justify="right")
    for a in result.artifacts:
        s = _score_style(a.overall, fail_under)
        table.add_row(
            Path(a.path).name,
            a.type.value,
            f"[{s}]{common.format_score(a.overall)}[/]",
            str(len(a.findings)),
        )
    console.print(table)

    # Prioritized "top fixes" — highest impact (severity × artifact weight) first.
    if top_fixes > 0:
        top = common.top_fixes(result, top_fixes)
        if top:
            console.print(f"\n[bold]Top {len(top)} fixes[/] [dim](highest impact first)[/]")
            for i, f in enumerate(top, start=1):
                _print_fix_line(console, f, i)

    # Findings grouped by artifact, severity-ordered, with fix suggestions.
    for a in result.artifacts:
        if not a.findings:
            continue
        console.print(f"\n[bold]{a.path}[/] [dim]({common.format_score(a.overall)}/100)[/]")
        for f in common.sort_findings(a.findings):
            sev_style = common.SEV_STYLE.get(f.severity, "white")
            tag = f" [dim]{f.pitfall_id}[/]" if f.pitfall_id else ""
            loc = f" [dim]:{f.line}[/]" if f.line else ""
            console.print(
                f"  [{sev_style}]{f.severity.value.upper():8}[/] "
                f"[dim]{f.dimension.value:14}[/]{tag}{loc} {f.message}"
            )
            console.print(f"           [green]fix[/] {f.suggestion}")

    label = common.pass_label(result.overall, fail_under)
    score = common.format_score(result.overall)
    if label == "FAIL":
        console.print(
            f"\n[bold red]FAIL[/] overall {score} < threshold {fail_under:.0f}"
        )
    else:
        console.print(f"\n[green]PASS[/] overall {score} ≥ {fail_under:.0f}")
