"""`sddgrade advise` — scan a codebase and recommend how to adopt Spec-Kit / SDD.

Heuristic-first so it always works with no LLM. It infers the stack, test posture, and
structure, then emits concrete, prioritized recommendations. (An LLM-enriched mode via
the judge backend is a natural follow-up.)
"""

from __future__ import annotations

from collections import Counter
from pathlib import Path

from rich.console import Console
from rich.panel import Panel

_LANG_BY_EXT = {
    ".py": "Python", ".ts": "TypeScript", ".tsx": "TypeScript", ".js": "JavaScript",
    ".jsx": "JavaScript", ".go": "Go", ".rs": "Rust", ".java": "Java", ".rb": "Ruby",
    ".php": "PHP", ".cs": "C#", ".kt": "Kotlin", ".swift": "Swift", ".scala": "Scala",
    ".c": "C", ".cpp": "C++", ".h": "C/C++",
}
_SKIP_DIRS = {
    ".git", "node_modules", ".venv", "venv", "dist", "build", "__pycache__",
    ".mypy_cache", ".pytest_cache", ".ruff_cache", ".next", "target", "vendor",
}


def _scan(root: Path) -> dict:
    langs: Counter = Counter()
    has_tests = False
    has_ci = (root / ".github" / "workflows").is_dir()
    has_speckit = (root / ".specify").is_dir() or (root / "specs").is_dir()
    manifests = 0
    file_count = 0

    for p in root.rglob("*"):
        if any(part in _SKIP_DIRS for part in p.parts):
            continue
        if p.is_dir():
            if p.name in {"tests", "test", "__tests__", "spec"}:
                has_tests = True
            continue
        file_count += 1
        ext = p.suffix.lower()
        if ext in _LANG_BY_EXT:
            langs[_LANG_BY_EXT[ext]] += 1
        if "test" in p.name.lower() or "spec" in p.name.lower():
            has_tests = True
        if p.name in {
            "package.json", "pyproject.toml", "go.mod", "Cargo.toml", "pom.xml",
            "build.gradle", "Gemfile", "composer.json",
        }:
            manifests += 1

    return {
        "languages": langs,
        "has_tests": has_tests,
        "has_ci": has_ci,
        "has_speckit": has_speckit,
        "monorepo": manifests > 1,
        "file_count": file_count,
    }


def _recommendations(info: dict) -> list[str]:
    recs: list[str] = []

    if info["has_speckit"]:
        recs.append(
            "Spec-Kit is already initialized here. Run `sddgrade review` on your "
            "specs/ to benchmark their quality and `sddgrade dashboard` to track trends."
        )
    else:
        recs.append(
            "Adopt Spec-Kit: `uv tool install specify-cli ...` then `specify init .`. "
            "Start with one feature: `/speckit.specify` → `/speckit.plan` → `/speckit.tasks`."
        )

    top = info["languages"].most_common(2)
    if top:
        lang_list = ", ".join(f"{n} ({c} files)" for n, c in top)
        recs.append(
            f"Primary stack: {lang_list}. Put these concrete choices in plan.md's "
            "Technical Context with a one-line rationale each; keep them OUT of spec.md."
        )

    if not info["has_tests"]:
        recs.append(
            "No test suite detected. Add a Test-First principle to your constitution so "
            "tasks.md generates failing tests before implementation."
        )
    else:
        recs.append(
            "Tests exist — encode Test-First and Integration-First as constitution "
            "principles so the gates in plan.md enforce them."
        )

    if info["monorepo"]:
        recs.append(
            "Monorepo detected (multiple package manifests). Use one specs/<feature> "
            "tree per service and a shared constitution; review each with "
            "`sddgrade review <path>`."
        )

    if info["has_ci"]:
        recs.append(
            "You have CI. Add a spec-quality gate: `sddgrade review --rules --fail-under "
            "70` (offline, deterministic) as a required check on PRs that touch specs/."
        )
    else:
        recs.append(
            "Add CI that runs `sddgrade review --rules --fail-under 70` so spec quality "
            "is gated like code quality."
        )

    # Architectural pattern hint.
    recs.append(
        "Architectural pattern to specify: Library-First — design each feature as a "
        "standalone module with a clear interface (and a CLI surface where it helps), so "
        "specs map cleanly to independently testable units."
    )
    return recs


def advise(path: Path, console: Console | None = None) -> int:
    console = console or Console()
    root = Path(path).resolve()
    info = _scan(root)

    langs = ", ".join(f"{n}:{c}" for n, c in info["languages"].most_common(5)) or "unknown"
    console.print(
        Panel(
            f"files=[bold]{info['file_count']}[/]  langs=[bold]{langs}[/]\n"
            f"tests={'yes' if info['has_tests'] else 'no'}  "
            f"ci={'yes' if info['has_ci'] else 'no'}  "
            f"spec-kit={'yes' if info['has_speckit'] else 'no'}  "
            f"monorepo={'yes' if info['monorepo'] else 'no'}",
            title=f"SDD adoption advice — {root.name}",
            expand=False,
        )
    )
    for i, rec in enumerate(_recommendations(info), start=1):
        console.print(f"  [bold cyan]{i}.[/] {rec}")
    return 0
