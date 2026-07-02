"""Command-line surface for sddgrade.

Deliberately small: five plain commands with sensible defaults, mirroring the
`specify` CLI. The common case is a bare ``sddgrade review``. Heavy modules are
imported lazily inside each command so the app loads fast and stays importable
while the codebase is built out.
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
    integration: str = typer.Option(
        "claude", "--integration", "-i",
        help="AI agent whose subscription runs the judge (claude, copilot, cursor, gemini, ...).",
    ),
    path: Path = typer.Argument(Path("."), help="Project root."),
) -> None:
    """Scaffold .sddgrade.toml and install the judge slash command into your agent."""
    from .integrations import agent as agent_backend

    written = agent_backend.scaffold(path, integration)
    typer.echo(f"Initialized sddgrade ({integration}). Wrote:")
    for p in written:
        typer.echo(f"  {p}")


@app.command()
def review(
    path: Path = typer.Argument(Path("."), help="Repo or specs directory to review."),
    rules: bool = typer.Option(False, "--rules", help="Deterministic lint only (no LLM)."),
    api: bool = typer.Option(False, "--api", help="Use the key-based API judge (CI/headless)."),
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
    tool: Tool = typer.Option(
        Tool.auto, "--tool", help="Toolchain: auto | speckit | openspec.",
    ),
) -> None:
    """Grade every Spec-Kit or OpenSpec artifact found under PATH."""
    from .runner import run_review

    backend = "rules" if rules else ("api" if api else "agent")
    exit_code = run_review(
        path, backend=backend, json_out=json_out, fail_under=fail_under,
        require_judge=require_judge, top_fixes=top_fixes, sarif_path=sarif,
        html_path=html, tool=tool.value,
    )
    raise typer.Exit(code=exit_code)


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


self_app = typer.Typer(no_args_is_help=True, help="Version checks and upgrades.")
app.add_typer(self_app, name="self")


@self_app.command("check")
def self_check() -> None:
    """Report the installed version (release check is a roadmap item)."""
    typer.echo(f"sddgrade {__version__}")


@self_app.command("upgrade")
def self_upgrade() -> None:
    """Upgrade sddgrade (delegates to your installer)."""
    typer.echo("Upgrade via your installer, e.g.:")
    typer.echo("  uv tool upgrade sddgrade")


@app.command("integration")
def integration_cmd(
    action: str = typer.Argument("list", help="Currently only 'list'."),
) -> None:
    """List supported AI agent integrations for the judge backend."""
    from .integrations import agent as agent_backend

    if action == "list":
        for name in agent_backend.supported_agents():
            typer.echo(name)
    else:
        typer.echo("Only 'list' is supported.")


if __name__ == "__main__":
    app()
