"""Terminal metrics dashboard over local review history.

Reads ``.sddgrade/history.jsonl`` and renders score trends (sparklines), the latest
per-artifact breakdown, and the most frequent pitfalls across runs. No browser.
"""

from __future__ import annotations

from collections import Counter
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from . import history

_SPARK = "▁▂▃▄▅▆▇█"


def sparkline(values: list[float], lo: float = 0.0, hi: float = 100.0) -> str:
    if not values:
        return ""
    span = (hi - lo) or 1.0
    out = []
    for v in values:
        frac = max(0.0, min(1.0, (v - lo) / span))
        out.append(_SPARK[round(frac * (len(_SPARK) - 1))])
    return "".join(out)


def _trend_arrow(values: list[float]) -> str:
    if len(values) < 2:
        return "[dim]—[/]"
    delta = values[-1] - values[-2]
    # Integer deltas: sub-point movement is judge noise, not signal (#59).
    if delta > 0.5:
        return f"[green]▲ +{max(1, round(delta))}[/]"
    if delta < -0.5:
        return f"[red]▼ {min(-1, round(delta))}[/]"
    return "[dim]≈[/]"


def show(path: Path, console: Console | None = None) -> int:
    console = console or Console()
    root = Path(path).resolve()
    runs = history.load(root)

    if not runs:
        console.print(
            f"[yellow]No review history under[/] {root}. "
            "Run [bold]sddgrade review[/] first."
        )
        return 0

    overalls = [r.get("overall", 0.0) for r in runs]
    latest = runs[-1]

    console.print(
        Panel(
            f"runs=[bold]{len(runs)}[/]  latest=[bold]{overalls[-1]:.0f}[/]  "
            f"{_trend_arrow(overalls)}\n"
            f"trend {sparkline(overalls)}  "
            f"[dim](min {min(overalls):.0f} / max {max(overalls):.0f})[/]",
            title="SDD quality — overall score history",
            expand=False,
        )
    )

    # Latest per-artifact breakdown.
    table = Table(title="Latest run — by artifact", expand=True)
    table.add_column("Artifact", overflow="fold")
    table.add_column("Type")
    table.add_column("Score", justify="right")
    table.add_column("Findings", justify="right")
    for a in latest.get("artifacts", []):
        table.add_row(
            Path(a.get("path", "")).name,
            a.get("type", ""),
            f"{a.get('overall', 0):.0f}",
            str(a.get("findings", 0)),
        )
    console.print(table)

    # Top recurring pitfalls across all runs.
    pit = Counter()
    for r in runs:
        for pid, count in (r.get("pitfalls") or {}).items():
            pit[pid] += count
    if pit:
        pt = Table(title="Top recurring pitfalls (all runs)", expand=True)
        pt.add_column("Pitfall")
        pt.add_column("Hits", justify="right")
        for pid, count in pit.most_common(10):
            pt.add_row(pid, str(count))
        console.print(pt)

    return 0
