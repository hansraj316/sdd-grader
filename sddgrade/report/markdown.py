"""Markdown report — a shareable artifact written next to the review."""

from __future__ import annotations

from ..model import ReviewResult
from . import common


def render(result: ReviewResult) -> str:
    lines: list[str] = []
    lines.append("# SDD Review Report")
    lines.append("")
    lines.append(f"- Tool: `{result.tool}`  •  Engine: `{result.engine}`")
    if result.timestamp:
        lines.append(f"- Generated: {result.timestamp}")
    lines.append(f"- **Overall score: {common.format_score(result.overall)}/100**")
    lines.append(f"- Coverage: `{result.coverage}`")
    lines.append("")
    lines.append(f"> **What this score proves:** {result.coverage_note}")
    lines.append("")

    lines.append("## Artifacts")
    lines.append("")
    lines.append("| Artifact | Type | Score | Findings |")
    lines.append("|----------|------|------:|---------:|")
    for a in result.artifacts:
        lines.append(
            f"| `{a.path}` | {a.type.value} | {common.format_score(a.overall)} "
            f"| {len(a.findings)} |"
        )
    lines.append("")

    for a in result.artifacts:
        if not a.findings:
            continue
        lines.append(f"## `{a.path}` — {common.format_score(a.overall)}/100")
        lines.append("")
        for f in common.sort_findings(a.findings):
            tag = f" [{f.pitfall_id}]" if f.pitfall_id else ""
            loc = f" (line {f.line})" if f.line else ""
            lines.append(
                f"- **{f.severity.value.upper()}** · {f.dimension.value}{tag}{loc}: "
                f"{f.message}"
            )
            lines.append(f"  - _Fix:_ {f.suggestion}")
        lines.append("")
    return "\n".join(lines)
