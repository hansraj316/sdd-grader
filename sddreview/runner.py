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
from .discovery import discover_artifacts, resolve_adapter
from .engine import lint as lint_mod
from .engine import scoring
from .model import Finding, ReviewResult
from .report import markdown
from .report import terminal as terminal_report
from .report.json_out import render as render_json


# Exit codes: 0 pass · 1 below threshold · 2 nothing to review · 3 judge required but unavailable
EXIT_PASS = 0
EXIT_FAIL = 1
EXIT_NO_ARTIFACTS = 2
EXIT_JUDGE_REQUIRED = 3


def run_review(
    path: Path,
    backend: str = "agent",
    json_out: bool = False,
    fail_under: float | None = None,
    write_markdown: bool = True,
    require_judge: bool = False,
    top_fixes: int = 0,
    sarif_path: Path | None = None,
    html_path: Path | None = None,
    tool: str | None = None,
    console: Console | None = None,
) -> int:
    console = console or Console()
    # When emitting machine-readable JSON, human warnings must go to stderr so
    # they don't corrupt the stdout JSON document.
    warn_console = Console(stderr=True) if json_out else console
    root = path.resolve()

    cfg = config_mod.load(root)
    if fail_under is not None:
        cfg.fail_under = fail_under
    if tool is not None:
        cfg.tool = tool

    artifacts = discover_artifacts(root, cfg.tool)
    if not artifacts:
        if json_out:
            console.print_json(data={"error": "no artifacts found", "root": str(root)})
        else:
            console.print(
                f"[yellow]No Spec-Kit artifacts found under[/] {root}. "
                "Expected specs/<feature>/spec.md (run `specify init` first)."
            )
        return EXIT_NO_ARTIFACTS

    adapter = resolve_adapter(root, cfg.tool)
    findings: list[Finding] = lint_mod.lint(artifacts, adapter, root)

    engine_label = "rules"
    if backend in ("agent", "api"):
        judge_findings, engine_label = _run_judge(artifacts, backend, root, cfg, warn_console)
        findings.extend(judge_findings)

    # --require-judge: fail loudly rather than silently scoring lint-only.
    if require_judge and engine_label == "rules":
        msg = (
            "judge required but unavailable: the semantic judge did not run, so this "
            "would be a lint-only score. Run the agent judge command (or use --api with "
            "a key), or drop --require-judge."
        )
        if json_out:
            sys.stdout.write(
                render_json(scoring.score(artifacts, findings, cfg, engine="rules"))
            )
            sys.stdout.write("\n")
        warn_console.print(f"[bold red]ERROR[/] {msg}")
        return EXIT_JUDGE_REQUIRED

    result: ReviewResult = scoring.score(artifacts, findings, cfg, engine=engine_label)
    result.timestamp = datetime.now(timezone.utc).isoformat()

    history.record(root, result)

    if sarif_path is not None:
        from .report import sarif as sarif_report

        sarif_path.parent.mkdir(parents=True, exist_ok=True)
        sarif_path.write_text(sarif_report.render(result, root=root), encoding="utf-8")
        if not json_out:
            console.print(f"[dim]SARIF written to {sarif_path}[/]")

    if html_path is not None:
        from .report import html as html_report

        html_path.parent.mkdir(parents=True, exist_ok=True)
        html_path.write_text(html_report.render(result, fail_under=cfg.fail_under), encoding="utf-8")
        if not json_out:
            console.print(f"[dim]HTML report written to {html_path}[/]")

    if json_out:
        # Plain stdout — never through rich, which would reflow/scramble the JSON.
        sys.stdout.write(render_json(result) + "\n")
    else:
        terminal_report.render(
            result, fail_under=cfg.fail_under, console=console, top_fixes=top_fixes
        )
        if write_markdown:
            md_path = root / ".sddreview" / "report.md"
            md_path.parent.mkdir(parents=True, exist_ok=True)
            md_path.write_text(markdown.render(result), encoding="utf-8")
            console.print(f"\n[dim]Markdown report written to {md_path}[/]")

    return EXIT_PASS if result.overall >= cfg.fail_under else EXIT_FAIL


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
