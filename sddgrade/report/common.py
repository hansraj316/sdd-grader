"""Shared presentation helpers for every report backend (#64).

Severity ordering/colors/labels, score formatting, the score band (pass/warn/fail),
finding sorting/location formatting, and the top-fixes selection all live here so the
five backends (terminal, markdown, html, sarif, json) are pure formatters and cannot
drift apart again.

Score precision (#59): human-facing reports render scores as integers — the judged
engine is not run-to-run reproducible, so a 73 vs 73.4 distinction is noise. The JSON
report keeps numeric scores for machines, rounded to at most 1 decimal (see
``model.ReviewResult.to_dict``).
"""

from __future__ import annotations

from pathlib import Path

from ..model import Finding, ReviewResult, Severity

# Highest severity first — the display order used by every backend.
SEV_ORDER: dict[Severity, int] = {
    s: i
    for i, s in enumerate(
        [Severity.CRITICAL, Severity.HIGH, Severity.MEDIUM, Severity.LOW, Severity.INFO]
    )
}

# Rich styles (terminal).
SEV_STYLE: dict[Severity, str] = {
    Severity.CRITICAL: "bold red",
    Severity.HIGH: "red",
    Severity.MEDIUM: "yellow",
    Severity.LOW: "cyan",
    Severity.INFO: "dim",
}

# Hex colors (html).
SEV_COLOR: dict[Severity, str] = {
    Severity.CRITICAL: "#b00020",
    Severity.HIGH: "#d32f2f",
    Severity.MEDIUM: "#f9a825",
    Severity.LOW: "#0288d1",
    Severity.INFO: "#757575",
}

# SARIF result levels (sarif).
SARIF_LEVEL: dict[Severity, str] = {
    Severity.CRITICAL: "error",
    Severity.HIGH: "error",
    Severity.MEDIUM: "warning",
    Severity.LOW: "note",
    Severity.INFO: "note",
}

# Below the gate is "fail"; between the gate and this is "warn"; above is "pass".
WARN_THRESHOLD = 85.0

# How many prioritized findings the display backends (terminal --top-fixes default,
# html) show. Chosen deliberately smaller than the JSON report's machine-facing cap
# of 10 (model.ReviewResult.to_dict) — humans get the short list, tools get more.
DEFAULT_TOP_FIXES = 5


def score_band(score: float, fail_under: float) -> str:
    """"fail" | "warn" | "pass" — the one place the banding thresholds live."""
    if score < fail_under:
        return "fail"
    if score < WARN_THRESHOLD:
        return "warn"
    return "pass"


def format_score(score: float) -> str:
    """Integer rendering for every human-facing score (#59)."""
    return f"{round(score)}"


def pass_label(score: float, fail_under: float) -> str:
    return "PASS" if score >= fail_under else "FAIL"


def sort_findings(findings: list[Finding]) -> list[Finding]:
    """Stable severity-descending order for display."""
    return sorted(findings, key=lambda f: SEV_ORDER.get(f.severity, 9))


def artifact_name(f: Finding) -> str:
    """Short display name for a finding's artifact ("?" when unattributed)."""
    return Path(f.artifact_path).name if f.artifact_path else "?"


def finding_location(f: Finding) -> str:
    """"name:12" / "name" — the artifact basename plus the line when known."""
    loc = f":{f.line}" if f.line else ""
    return f"{artifact_name(f)}{loc}"


def top_fixes(result: ReviewResult, n: int = DEFAULT_TOP_FIXES) -> list[Finding]:
    """The n highest-impact findings (severity x artifact weight)."""
    return result.prioritized_findings()[:n]
