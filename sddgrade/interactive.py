"""Interactive `sddgrade init` wizard, mirroring the feel of `specify init`.

Only ever entered when the user gave no ``--integration`` flag AND both stdin
and stdout are TTYs (cli.py enforces that); everything here may therefore
assume a human is present. Arrow-key selection uses readchar + a rich Live
panel exactly like Spec-Kit's `select_with_arrows`; if readchar is somehow
unavailable we degrade to a numbered prompt rather than crash.
"""

from __future__ import annotations

import sys
from pathlib import Path

import typer
from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.table import Table

# Selection order mirrors init --help; descriptions are the human names.
AGENT_CHOICES: dict[str, str] = {
    "claude": "Claude Code",
    "copilot": "GitHub Copilot",
    "cursor": "Cursor",
    "gemini": "Gemini CLI",
    "windsurf": "Windsurf",
    "codex": "Codex CLI",
    "generic": "Any other agent (.sddgrade/commands/)",
}


def _get_key() -> str:
    """One keypress, normalized. Cross-platform via readchar (as Spec-Kit does)."""
    import readchar

    key = readchar.readkey()
    if key in (readchar.key.UP, readchar.key.CTRL_P):
        return "up"
    if key in (readchar.key.DOWN, readchar.key.CTRL_N):
        return "down"
    if key == readchar.key.ENTER:
        return "enter"
    if key == readchar.key.ESC:
        return "escape"
    if key == readchar.key.CTRL_C:
        raise KeyboardInterrupt
    return key


def _numbered_select(options: dict[str, str], prompt_text: str, default_key: str) -> str:
    """Plain numbered fallback when arrow-key input isn't available."""
    keys = list(options)
    typer.echo(prompt_text)
    for i, key in enumerate(keys, start=1):
        typer.echo(f"  {i}. {key} ({options[key]})")
    default_index = keys.index(default_key) + 1 if default_key in keys else 1
    while True:
        raw = typer.prompt("Number", default=str(default_index))
        try:
            n = int(raw)
        except ValueError:
            n = 0
        if 1 <= n <= len(keys):
            return keys[n - 1]
        typer.echo(f"Enter a number between 1 and {len(keys)}.")


def select_with_arrows(
    options: dict[str, str],
    prompt_text: str = "Select an option",
    default_key: str | None = None,
    console: Console | None = None,
) -> str:
    """Arrow-key selection in a rich Live panel (Spec-Kit style).

    ↑/↓ move, Enter selects, Esc/Ctrl+C cancels (exit code 1). Falls back to a
    numbered prompt if readchar can't be imported.
    """
    try:
        import readchar  # noqa: F401
    except ImportError:
        return _numbered_select(options, prompt_text, default_key or next(iter(options)))

    console = console or Console(highlight=False)
    keys = list(options)
    index = keys.index(default_key) if default_key in keys else 0

    def panel() -> Panel:
        grid = Table.grid(padding=(0, 2))
        grid.add_column(style="cyan", justify="left", width=3)
        grid.add_column(style="white", justify="left")
        for i, key in enumerate(keys):
            marker = "▶" if i == index else " "
            grid.add_row(marker, f"[cyan]{key}[/] [dim]({options[key]})[/]")
        grid.add_row("", "")
        grid.add_row("", "[dim]Use ↑/↓ to navigate, Enter to select, Esc to cancel[/dim]")
        return Panel(grid, title=f"[bold]{prompt_text}[/]", border_style="cyan", padding=(1, 2))

    console.print()
    transient = sys.platform != "win32"
    with Live(panel(), console=console, transient=transient, auto_refresh=False) as live:
        while True:
            try:
                key = _get_key()
            except KeyboardInterrupt:
                console.print("\n[yellow]Selection cancelled[/]")
                raise typer.Exit(code=1)
            if key == "up":
                index = (index - 1) % len(keys)
            elif key == "down":
                index = (index + 1) % len(keys)
            elif key == "enter":
                return keys[index]
            elif key == "escape":
                console.print("\n[yellow]Selection cancelled[/]")
                raise typer.Exit(code=1)
            live.update(panel(), refresh=True)


def _detect_toolchains(root: Path) -> list[str]:
    """Which spec toolchain layouts are actually present under root."""
    from .discovery import get_adapter

    return [name for name in ("speckit", "openspec") if get_adapter(name).detect(root)]


def run_init_wizard(path: Path, console: Console | None = None) -> list[Path]:
    """Banner already shown by cli.py; select agent → detect toolchain → scaffold → next steps."""
    from .integrations import agent as agent_backend

    console = console or Console(highlight=False)
    root = Path(path).resolve()

    selected = select_with_arrows(
        AGENT_CHOICES, "Choose your agent integration:", "claude", console=console
    )

    found = _detect_toolchains(root)
    if found:
        toolchain = " + ".join(found) + " [dim](detected)[/]"
    else:
        toolchain = "none detected [dim](will auto-detect at review time)[/]"

    setup = [
        "[cyan]sddgrade project setup[/]",
        "",
        f"{'Path':<12} [dim]{root}[/]",
        f"{'Integration':<12} [green]{selected}[/] [dim]({AGENT_CHOICES[selected]})[/]",
        f"{'Toolchain':<12} {toolchain}",
    ]
    console.print(Panel("\n".join(setup), border_style="cyan", padding=(1, 2)))

    written = agent_backend.scaffold(root, selected)
    console.print("[green]✓[/] Initialized sddgrade. Wrote:")
    for p in written:
        console.print(f"  [dim]{p}[/]")

    steps = [
        f"1. Open [cyan]{AGENT_CHOICES[selected]}[/] in this project and run the "
        "[cyan]/sddgrade[/] command — your agent judges the specs and writes "
        "[dim].sddgrade/judge.json[/]",
        "2. Run [cyan]sddgrade review[/] — grades every artifact (lint + that judgment)",
        "3. Optional: gate CI with [cyan]sddgrade review --fail-under 70[/]",
    ]
    console.print()
    console.print(
        Panel("\n".join(steps), title="Next Steps", border_style="cyan", padding=(1, 2))
    )
    return written
