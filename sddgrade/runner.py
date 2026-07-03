"""Orchestrates a review: discover → lint → (judge) → score → report → history.

This is the single place the CLI's ``review`` command calls into, so the pipeline
is testable without Typer. Returns a process exit code (see EXIT_* below).

Stream contract: the report itself goes to stdout; every diagnostic (warnings,
notices, errors) goes to stderr, so ``--json`` output is always parseable and
``review > out.json`` stays clean.
"""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

from rich.console import Console
from rich.markup import escape

from . import config as config_mod
from . import history
from .discovery import discover_artifacts, resolve_adapter
from .engine import lint as lint_mod
from .engine import scoring
from .model import Finding, ReviewResult
from .report import markdown
from .report import terminal as terminal_report
from .report.json_out import render as render_json


# Exit codes: 0 pass · 1 below an explicitly requested --fail-under/config threshold
# · 2 nothing to review · 3 judge required but unavailable · 4 config file unusable
EXIT_PASS = 0
EXIT_FAIL = 1
EXIT_NO_ARTIFACTS = 2
EXIT_JUDGE_REQUIRED = 3
EXIT_CONFIG_ERROR = 4

# Score-coloring threshold for reports when no gate is configured. Display only —
# it never affects the exit code.
DISPLAY_FAIL_UNDER = 70.0


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
    err_console: Console | None = None,
) -> int:
    # Diagnostics go to err_console (stderr by default) so stdout stays parseable
    # under --json. When a caller injects only `console` (tests), it takes both roles.
    if err_console is None:
        err_console = console if console is not None else Console(stderr=True)
    console = console or Console()
    root = path.resolve()

    try:
        cfg = config_mod.load(root)
    except config_mod.ConfigError as exc:
        # soft_wrap: file paths must survive intact for grep/tests; escape: TOML
        # errors contain [brackets] rich would parse as markup.
        err_console.print(f"[bold red]ERROR[/] {escape(str(exc))}", soft_wrap=True)
        return EXIT_CONFIG_ERROR
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
    judge_error: str | None = None
    if backend in ("agent", "api"):
        judge_findings, engine_label, judge_error = _run_judge(
            artifacts, backend, root, cfg, err_console
        )
        # Drop judge findings whose (pitfall_id, artifact_path) is already covered by
        # a lint finding. method="both" pitfalls are linted deterministically; without
        # dedup the same defect is double-penalised, making hybrid scores systematically
        # lower than rules-only scores for identical artifacts.
        lint_keys: set[tuple[str | None, str | None]] = {
            (f.pitfall_id, f.artifact_path) for f in findings
        }
        deduplicated = [
            f for f in judge_findings
            if (f.pitfall_id, f.artifact_path) not in lint_keys
        ]
        findings.extend(deduplicated)

    # Explicitly requesting the API judge (`--api`) implies --require-judge: someone
    # gating CI on the key-based backend wants a hard failure when it can't run, not a
    # silently weaker lint-only score. The interactive agent default stays forgiving.
    if backend == "api":
        require_judge = True

    if judge_error is not None and not require_judge:
        # escape(): exception text may contain [brackets] rich would eat as markup.
        err_console.print(
            f"[yellow]Judge unavailable[/] ({escape(judge_error)}); running rules-only."
        )

    # --require-judge (and any explicitly requested backend): fail loudly rather than
    # silently scoring lint-only.
    if require_judge and engine_label == "rules":
        if backend == "api":
            msg = (
                f"the --api judge failed to run: {judge_error}. Refusing to emit a "
                "lint-only score as if it were the requested lint+semantic review. "
                "Fix the API setup (set ANTHROPIC_API_KEY, install `sddgrade[api]`, "
                "check network/model access) or run without --api to accept lint-only."
            )
        else:
            msg = (
                "judge required but unavailable"
                + (f" ({judge_error})" if judge_error else "")
                + ": the semantic judge did not run, so this would be a lint-only "
                "score. Run the agent judge command (or use --api with a key), or "
                "drop --require-judge."
            )
        if json_out:
            sys.stdout.write(
                render_json(scoring.score(artifacts, findings, cfg, engine="rules"))
            )
            sys.stdout.write("\n")
        err_console.print(f"[bold red]ERROR[/] {escape(msg)}")
        return EXIT_JUDGE_REQUIRED

    result: ReviewResult = scoring.score(artifacts, findings, cfg, engine=engine_label)
    result.timestamp = datetime.now(timezone.utc).isoformat()

    history.record(root, result)

    # Reports color scores against the configured gate, or 70 when no gate is set.
    display_fail_under = cfg.fail_under if cfg.fail_under is not None else DISPLAY_FAIL_UNDER

    if sarif_path is not None:
        from .report import sarif as sarif_report

        sarif_path.parent.mkdir(parents=True, exist_ok=True)
        sarif_path.write_text(sarif_report.render(result, root=root), encoding="utf-8")
        err_console.print(f"[dim]SARIF written to {sarif_path}[/]")

    if html_path is not None:
        from .report import html as html_report

        html_path.parent.mkdir(parents=True, exist_ok=True)
        html_path.write_text(
            html_report.render(result, fail_under=display_fail_under), encoding="utf-8"
        )
        err_console.print(f"[dim]HTML report written to {html_path}[/]")

    if json_out:
        # Plain stdout — never through rich, which would reflow/scramble the JSON.
        sys.stdout.write(render_json(result) + "\n")
    else:
        terminal_report.render(
            result, fail_under=display_fail_under, console=console, top_fixes=top_fixes
        )
        if write_markdown:
            md_path = root / ".sddgrade" / "report.md"
            md_path.parent.mkdir(parents=True, exist_ok=True)
            md_path.write_text(markdown.render(result), encoding="utf-8")
            err_console.print(f"\n[dim]Markdown report written to {md_path}[/]")

    # Gating is opt-in: findings alone never fail the exit code unless the user
    # asked for a threshold via --fail-under or the config file.
    if cfg.fail_under is None:
        return EXIT_PASS
    return EXIT_PASS if result.overall >= cfg.fail_under else EXIT_FAIL


def _run_judge(artifacts, backend, root, cfg, err_console):
    """Run the semantic judge if available.

    Returns ``(findings, engine_label, error)``. On failure the error string carries
    the reason so the caller can decide whether to degrade to rules (agent default)
    or fail the run (--require-judge / explicit --api) — never swallow it.
    """
    try:
        from .engine import judge as judge_mod
    except Exception as exc:  # judge not built yet
        return [], "rules", f"judge engine unavailable: {exc}"

    try:
        findings = judge_mod.judge(artifacts, backend, root, cfg, console=err_console)
        return findings, backend, None
    except judge_mod.JudgeUnavailable as exc:  # type: ignore[attr-defined]
        return [], "rules", str(exc)
