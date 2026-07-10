"""ASCII-art banner for interactive runs, mirroring Spec-Kit's `specify` banner.

Strict display contract: the banner appears ONLY when a human is watching —
never under ``--json``, never when stdout is piped/redirected (CI, subprocess
tests, `review > out.json`), and never inside reports. Callers go through
``maybe_show_banner`` which enforces the TTY check; ``show_banner`` itself is
unconditional so tests can render it to a capture console.
"""

from __future__ import annotations

import sys

from rich.align import Align
from rich.console import Console
from rich.text import Text

BANNER = """
███████╗██████╗ ██████╗  ██████╗ ██████╗  █████╗ ██████╗ ███████╗
██╔════╝██╔══██╗██╔══██╗██╔════╝ ██╔══██╗██╔══██╗██╔══██╗██╔════╝
███████╗██║  ██║██║  ██║██║  ███╗██████╔╝███████║██║  ██║█████╗
╚════██║██║  ██║██║  ██║██║   ██║██╔══██╗██╔══██║██║  ██║██╔══╝
███████║██████╔╝██████╔╝╚██████╔╝██║  ██║██║  ██║██████╔╝███████╗
╚══════╝╚═════╝ ╚═════╝  ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝╚═════╝ ╚══════╝
"""

TAGLINE = "Grade specs like code"

# Per-line gradient, same mechanism as Spec-Kit's banner.
_COLORS = ["bright_blue", "blue", "cyan", "bright_cyan", "white", "bright_white"]


def show_banner(console: Console | None = None) -> None:
    """Print the banner unconditionally (callers gate via maybe_show_banner)."""
    console = console or Console(highlight=False)
    styled = Text()
    for i, line in enumerate(BANNER.strip("\n").splitlines()):
        styled.append(line + "\n", style=_COLORS[i % len(_COLORS)])
    console.print(Align.center(styled))
    console.print(Align.center(Text(TAGLINE, style="italic bright_yellow")))
    console.print()


def maybe_show_banner(console: Console | None = None) -> bool:
    """Show the banner only when stdout is an interactive terminal.

    Returns True if it was shown. Pipes, redirects, and CI stay byte-clean:
    subprocess tests assert stdout is parseable, so nothing may leak here.
    """
    if not sys.stdout.isatty():
        return False
    show_banner(console)
    return True
