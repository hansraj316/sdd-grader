"""Orchestrates a review: discover → lint → (judge) → score → report → history.

This is the single place the CLI's ``review`` command calls into, so the pipeline
is testable without Typer. Returns a process exit code (0 pass, 1 below threshold,
2 nothing to review).
"""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

from rich.console import Console

from . import config as config_mod
from . import history
from .discovery import discover_artifacts, get_adapter
from .engine import lint as lint_mod
from .engine import scoring
from .model import Finding, ReviewResult
from .report import markdown
from .report import terminal as terminal_report
from .report.json_out import render as render_json


def run_review(
    path: Path,
    backend: str = "agent",
    json_out: bool = False,
    fail_under: float | None = None,
    write_markdown: bool = True,
    console: Console | None = None,
) -> int:
    console = console or Console()
    root = path.resolve()

    cfg = config_mod.load(root)
    if fail_under is not None:
        cfg.fail_under = fail_under

    artifacts = discover_artifacts(root, cfg.tool)
    if not artifacts:
        if json_out:
            console.print_json(data={"error": "no artifacts found", "root": str(root)})
        else:
            console.print(
                f"[yellow]No Spec-Kit artifacts found under[/] {root}. "
                "Expected specs/<feature>/spec.md (run `specify init` first)."
            )
        return 2

    adapter = get_adapter(cfg.tool)
    findings: list[Finding] = lint_mod.lint(artifacts, adapter, root)

    engine_label = "rules"
    if backend in ("agent", "api"):
        judge_findings, engine_label = _run_judge(artifacts, backend, root, cfg, console)
        findings.extend(judge_findings)

    result: ReviewResult = scoring.score(artifacts, findings, cfg, engine=engine_label)
    result.timestamp = datetime.now(timezone.utc).isoformat()

    history.record(root, result)

    if json_out:
        # Plain stdout — never through rich, which would reflow/scramble the JSON.
        sys.stdout.write(render_json(result) + "\n")
    else:
        terminal_report.render(result, fail_under=cfg.fail_under, console=console)
        if write_markdown:
            md_path = root / ".sddreview" / "report.md"
            md_path.parent.mkdir(parents=True, exist_ok=True)
            md_path.write_text(markdown.render(result), encoding="utf-8")
            console.print(f"\n[dim]Markdown report written to {md_path}[/]")

    return 0 if result.overall >= cfg.fail_under else 1


def _run_judge(artifacts, backend, root, cfg, console):
    """Run the semantic judge if available; degrade to rules cleanly otherwise."""
    try:
        from .engine import judge as judge_mod
    except Exception:  # judge not built yet
        return [], "rules"

    try:
        findings = judge_mod.judge(artifacts, backend, root, cfg, console=console)
        return findings, backend
    except judge_mod.JudgeUnavailable as exc:  # type: ignore[attr-defined]
        console.print(f"[yellow]Judge unavailable[/] ({exc}); running rules-only.")
        return [], "rules"
