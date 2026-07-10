"""Rich terminal report — the default human-facing output of `sddgrade review`.

Renders summary-first, in a fixed order a human can scan top-to-bottom:
  1. Summary panel — overall score, PASS/FAIL vs the gate, coverage, a one-line verdict.
  2. Scores table — one row per artifact, worst-first, color-coded.
  3. Findings tables — grouped by artifact: Severity | Dimension | Line | Finding | Fix.
  4. Next steps — 2-3 contextual suggestions.

Every data element of the result is shown somewhere (nothing is dropped relative
to the JSON report's human-facing fields); scores render as integers via
report/common.format_score (#59).
"""

from __future__ import annotations

from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from ..model import ArtifactReview, Finding, ReviewResult, Severity
from . import common

_BAND_STYLE = {"fail": "bold red", "warn": "yellow", "pass": "green"}


def _score_style(score: float, fail_under: float) -> str:
    return _BAND_STYLE[common.score_band(score, fail_under)]


def _verdict(result: ReviewResult, fail_under: float) -> str:
    """One readable sentence: how many artifacts need work and where to start."""
    n = len(result.artifacts)
    plural = "s" if n != 1 else ""
    findings = result.all_findings
    if not findings:
        return f"All {n} artifact{plural} clean — no findings."
    failing = [a for a in result.artifacts if a.overall < fail_under]
    severe = [
        f for f in findings if f.severity in (Severity.CRITICAL, Severity.HIGH)
    ]
    head = (
        f"{len(failing)} of {n} artifact{plural} need{'s' if len(failing) == 1 else ''} work"
        if failing
        else f"All {n} artifact{plural} pass the gate"
    )
    if severe:
        tail = f"{len(severe)} high-severity finding{'s' if len(severe) != 1 else ''}"
    else:
        tail = f"{len(findings)} minor finding{'s' if len(findings) != 1 else ''}"
    worst = min(result.artifacts, key=lambda a: a.overall)
    return f"{head}; {tail} — start with {Path(worst.path).name}."


def _summary_panel(result: ReviewResult, fail_under: float) -> Panel:
    style = _score_style(result.overall, fail_under)
    label = common.pass_label(result.overall, fail_under)
    label_style = "green" if label == "PASS" else "bold red"
    coverage = (
        f"[green]coverage[/] {result.coverage}"
        if result.judge_used
        else f"[yellow]coverage[/] [yellow]{result.coverage}[/]"
    )
    judge_model = f" judge={result.judge_model}" if result.judge_model else ""
    lines = [
        f"[bold {style}]{common.format_score(result.overall)}[/][dim]/100[/]   "
        f"[{label_style}]{label}[/] [dim](gate {fail_under:.0f})[/]",
        "",
        f"{coverage} [dim]— {result.coverage_note}[/]",
        f"[dim]tool={result.tool} engine={result.engine}{judge_model} "
        f"artifacts={len(result.artifacts)} findings={len(result.all_findings)}[/]",
        "",
        _verdict(result, fail_under),
    ]
    return Panel("\n".join(lines), title="SDD Review", expand=False, padding=(0, 2))


def _worst_severity(a: ArtifactReview) -> Severity | None:
    findings = a.findings
    if not findings:
        return None
    return min(findings, key=lambda f: common.SEV_ORDER.get(f.severity, 9)).severity


def _scores_table(result: ReviewResult, fail_under: float) -> Table:
    table = Table(title="Scores", show_lines=False, expand=True, title_justify="left")
    table.add_column("Artifact", overflow="fold")
    table.add_column("Type")
    table.add_column("Score /100", justify="right")
    table.add_column("Findings", justify="right")
    table.add_column("Worst severity")
    for a in _worst_first(result):
        s = _score_style(a.overall, fail_under)
        worst = _worst_severity(a)
        worst_cell = (
            f"[{common.SEV_STYLE.get(worst, 'white')}]{worst.value.upper()}[/]"
            if worst
            else "[dim]—[/]"
        )
        table.add_row(
            f"[{s}]{Path(a.path).name}[/]",
            a.type.value,
            f"[{s}]{common.format_score(a.overall)}[/]",
            str(len(a.findings)),
            worst_cell,
        )
    return table


def _worst_first(result: ReviewResult) -> list[ArtifactReview]:
    return sorted(result.artifacts, key=lambda a: (a.overall, a.path))


def _findings_table(a: ArtifactReview, fail_under: float) -> Table:
    s = _score_style(a.overall, fail_under)
    table = Table(
        title=f"{a.path} [{s}]({common.format_score(a.overall)}/100)[/]",
        show_lines=True,
        expand=True,
        title_justify="left",
    )
    table.add_column("Severity", no_wrap=True)
    table.add_column("Dimension", no_wrap=True)
    table.add_column("Line", justify="right", no_wrap=True)
    table.add_column("Finding", ratio=2, overflow="fold")
    table.add_column("Fix", ratio=2, overflow="fold", style="green")
    for f in common.sort_findings(a.findings):
        sev_style = common.SEV_STYLE.get(f.severity, "white")
        tag = f" [dim]{f.pitfall_id}[/]" if f.pitfall_id else ""
        table.add_row(
            f"[{sev_style}]{f.severity.value.upper()}[/]",
            f.dimension.value,
            str(f.line) if f.line else "—",
            f"{f.message}{tag}",
            f.suggestion,
        )
    return table


def _print_fix_line(console: Console, f: Finding, index: int) -> None:
    sev_style = common.SEV_STYLE.get(f.severity, "white")
    tag = f" [dim]{f.pitfall_id}[/]" if f.pitfall_id else ""
    console.print(
        f"  [bold]{index}.[/] [{sev_style}]{f.severity.value.upper()}[/] "
        f"[dim]{common.finding_location(f)}{tag}[/] {f.message}"
    )
    console.print(f"     [green]fix[/] {f.suggestion}")


def _next_steps(result: ReviewResult) -> list[str]:
    """2-3 contextual suggestions, most valuable first."""
    tips: list[str] = []
    if not result.judge_used:
        tips.append(
            "Semantic judge didn't run — run your agent's [cyan]/sddgrade[/] command "
            "(or [cyan]sddgrade review --api[/]), then re-run [cyan]sddgrade review[/]."
        )
    if result.all_findings:
        tips.append(
            "Work through the fixes above (worst artifact first), then re-run "
            "[cyan]sddgrade review[/]."
        )
        tips.append(
            "Get a shareable report with [cyan]--html report.html[/], or just the "
            "shortlist with [cyan]--top-fixes 5[/]."
        )
    else:
        tips.append(
            "Specs are clean — gate CI with [cyan]sddgrade review --fail-under 70[/]."
        )
        tips.append("Track score trends over time with [cyan]sddgrade dashboard[/].")
    return tips[:3]


def render(
    result: ReviewResult,
    fail_under: float = 70.0,
    console: Console | None = None,
    top_fixes: int = 0,
) -> None:
    console = console or Console()

    # 1. Summary first: score, gate verdict, coverage, one-line human verdict.
    console.print(_summary_panel(result, fail_under))

    # 2. Per-artifact scores, worst-first.
    console.print()
    console.print(_scores_table(result, fail_under))

    # Prioritized "top fixes" — highest impact (severity × artifact weight) first.
    if top_fixes > 0:
        top = common.top_fixes(result, top_fixes)
        if top:
            console.print(f"\n[bold]Top {len(top)} fixes[/] [dim](highest impact first)[/]")
            for i, f in enumerate(top, start=1):
                _print_fix_line(console, f, i)

    # 3. Findings tables grouped by artifact, worst artifact first.
    for a in _worst_first(result):
        if not a.findings:
            continue
        console.print()
        console.print(_findings_table(a, fail_under))

    # 4. Next steps footer.
    steps = _next_steps(result)
    console.print()
    console.print(
        Panel(
            "\n".join(f"• {tip}" for tip in steps),
            title="Next steps",
            expand=False,
            padding=(0, 2),
        )
    )
