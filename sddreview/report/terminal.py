"""Rich terminal report — the default human-facing output of `sddreview review`."""

from __future__ import annotations

from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from ..model import ReviewResult, Severity

_SEV_STYLE = {
    Severity.CRITICAL: "bold red",
    Severity.HIGH: "red",
    Severity.MEDIUM: "yellow",
    Severity.LOW: "cyan",
    Severity.INFO: "dim",
}
_SEV_ORDER = {s: i for i, s in enumerate([
    Severity.CRITICAL, Severity.HIGH, Severity.MEDIUM, Severity.LOW, Severity.INFO
])}


def _score_style(score: float, fail_under: float) -> str:
    if score < fail_under:
        return "bold red"
    if score < 85:
        return "yellow"
    return "green"


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
            f"[{style}]{result.overall:.1f}/100[/]   "
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
            f"[{s}]{a.overall:.0f}[/]",
            str(len(a.findings)),
        )
    console.print(table)

    # Prioritized "top fixes" — highest impact (severity × artifact weight) first.
    if top_fixes > 0:
        top = result.prioritized_findings()[:top_fixes]
        if top:
            console.print(f"\n[bold]Top {len(top)} fixes[/] [dim](highest impact first)[/]")
            for i, f in enumerate(top, start=1):
                sev_style = _SEV_STYLE.get(f.severity, "white")
                tag = f" [dim]{f.pitfall_id}[/]" if f.pitfall_id else ""
                loc = f":{f.line}" if f.line else ""
                name = Path(f.artifact_path).name if f.artifact_path else "?"
                console.print(
                    f"  [bold]{i}.[/] [{sev_style}]{f.severity.value.upper()}[/] "
                    f"[dim]{name}{loc}{tag}[/] {f.message}"
                )
                console.print(f"     [green]fix[/] {f.suggestion}")

    # Findings grouped by artifact, severity-ordered, with fix suggestions.
    for a in result.artifacts:
        if not a.findings:
            continue
        console.print(f"\n[bold]{a.path}[/] [dim]({a.overall:.0f}/100)[/]")
        for f in sorted(a.findings, key=lambda x: _SEV_ORDER.get(x.severity, 9)):
            sev_style = _SEV_STYLE.get(f.severity, "white")
            tag = f" [dim]{f.pitfall_id}[/]" if f.pitfall_id else ""
            loc = f" [dim]:{f.line}[/]" if f.line else ""
            console.print(
                f"  [{sev_style}]{f.severity.value.upper():8}[/] "
                f"[dim]{f.dimension.value:14}[/]{tag}{loc} {f.message}"
            )
            console.print(f"           [green]fix[/] {f.suggestion}")

    if result.overall < fail_under:
        console.print(
            f"\n[bold red]FAIL[/] overall {result.overall:.1f} < threshold {fail_under:.0f}"
        )
    else:
        console.print(f"\n[green]PASS[/] overall {result.overall:.1f} ≥ {fail_under:.0f}")
