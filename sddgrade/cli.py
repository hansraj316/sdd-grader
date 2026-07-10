"""Command-line surface for sddgrade.

Deliberately small: five plain commands (init, review, advise, dashboard, plus the
judge-prompt plumbing command the scaffolded shim calls) with sensible defaults,
mirroring the `specify` CLI. The common case is a bare ``sddgrade review``. Heavy
modules are imported lazily inside each command so the app loads fast and stays
importable while the codebase is built out.
"""

from __future__ import annotations

from enum import Enum
from pathlib import Path

import typer

from . import __version__


class Tool(str, Enum):
    """Supported spec toolchains; Typer rejects anything else with the valid choices."""

    auto = "auto"
    speckit = "speckit"
    openspec = "openspec"


app = typer.Typer(
    add_completion=False,
    no_args_is_help=True,
    help="Review & benchmark Spec-Driven Development artifacts (GitHub Spec-Kit).",
)


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"sddgrade {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    _version: bool = typer.Option(
        False, "--version", callback=_version_callback, is_eager=True,
        help="Show version and exit.",
    ),
) -> None:
    """sddgrade — the external quality gate for Spec-Kit artifacts."""


@app.command()
def init(
    integration: str | None = typer.Option(
        None, "--integration", "-i",
        help="AI agent whose subscription runs the judge: "
        "claude | codex | copilot | cursor | gemini | windsurf | generic. "
        "Omit to choose interactively (defaults to claude when not a terminal).",
    ),
    path: Path = typer.Argument(Path("."), help="Project root."),
) -> None:
    """Scaffold .sddgrade.toml and install the judge slash command into your agent."""
    import sys

    from .banner import maybe_show_banner
    from .integrations import agent as agent_backend

    maybe_show_banner()

    if integration is None:
        if sys.stdin.isatty() and sys.stdout.isatty():
            # Guided setup (Spec-Kit style): arrow-key agent selection, toolchain
            # detection, scaffold, next-steps panel.
            from .interactive import run_init_wizard

            run_init_wizard(path)
            return
        # Non-interactive with no flag: same behavior as before, defaulting to
        # claude; the note goes to stderr so piped stdout stays unchanged.
        typer.echo(
            "Non-interactive session: defaulting to --integration claude.", err=True
        )
        integration = "claude"

    supported = agent_backend.supported_agents()
    if integration not in supported:
        raise typer.BadParameter(
            f"unknown integration {integration!r}; supported: {', '.join(supported)}",
            param_hint="--integration",
        )
    written = agent_backend.scaffold(path, integration)
    typer.echo(f"Initialized sddgrade ({integration}). Wrote:")
    for p in written:
        typer.echo(f"  {p}")


@app.command()
def review(
    path: Path = typer.Argument(Path("."), help="Repo or specs directory to review."),
    rules: bool = typer.Option(False, "--rules", help="Deterministic lint only (no LLM)."),
    api: bool = typer.Option(
        False, "--api",
        help="Use the key-based API judge (CI/headless). Fails (exit 3) if it can't run.",
    ),
    json_out: bool = typer.Option(False, "--json", help="Emit machine-readable JSON."),
    fail_under: float | None = typer.Option(
        None, "--fail-under",
        help="Exit non-zero if overall score is below N (CI gate; off unless set "
        "here or via fail_under in .sddgrade.toml).",
    ),
    require_judge: bool = typer.Option(
        False, "--require-judge",
        help="Fail (exit 3) instead of degrading to lint-only when the judge is unavailable.",
    ),
    top_fixes: int = typer.Option(
        0, "--top-fixes", help="Show the top N highest-impact fixes first (0 = off).",
    ),
    sarif: Path | None = typer.Option(
        None, "--sarif", help="Write SARIF 2.1.0 to this path (for GitHub code scanning).",
    ),
    html: Path | None = typer.Option(
        None, "--html", help="Write a self-contained HTML report (findings + fixes) to this path.",
    ),
    # Default None (not "auto") so an unset flag is distinguishable from an explicit
    # `--tool auto`: precedence is explicit flag > .sddgrade.toml `tool` > auto (#31).
    tool: Tool | None = typer.Option(
        None, "--tool",
        help="Toolchain: auto | speckit | openspec "
        "(default: `tool` from .sddgrade.toml, else auto).",
    ),
) -> None:
    """Grade every Spec-Kit or OpenSpec artifact found under PATH."""
    from .runner import run_review

    if not json_out:
        # Banner only for humans: maybe_show_banner is a no-op when stdout is
        # piped, and --json stdout must stay pure JSON.
        from .banner import maybe_show_banner

        maybe_show_banner()

    backend = "rules" if rules else ("api" if api else "agent")
    exit_code = run_review(
        path, backend=backend, json_out=json_out, fail_under=fail_under,
        require_judge=require_judge, top_fixes=top_fixes, sarif_path=sarif,
        html_path=html, tool=None if tool is None else tool.value,
    )
    raise typer.Exit(code=exit_code)


@app.command("judge-prompt")
def judge_prompt(
    path: Path = typer.Argument(Path("."), help="Project root."),
) -> None:
    """Print the current judge instructions for this repo's detected toolchain.

    The scaffolded agent command runs this instead of carrying baked-in guidance,
    so the pitfall catalog and artifact paths are always the installed version's.
    """
    from .integrations import agent as agent_backend

    typer.echo(agent_backend.judge_instructions(path))


@app.command()
def advise(
    path: Path = typer.Argument(Path("."), help="Codebase to analyze."),
) -> None:
    """Scan the codebase and recommend how to adopt Spec-Kit / SDD."""
    from .advisor import advise as run_advise

    run_advise(path)


@app.command()
def dashboard(
    path: Path = typer.Argument(Path("."), help="Repo whose .sddgrade history to show."),
) -> None:
    """Show a terminal metrics dashboard over local review history."""
    from .dashboard import show

    show(path)


if __name__ == "__main__":
    app()
