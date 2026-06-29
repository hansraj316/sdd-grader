"""Self-contained HTML report — shareable findings + fix suggestions, no dependencies.

Renders one standalone `.html` file (inline CSS, no external assets) with the overall
score, the engine-coverage caveat, a top-fixes list, and every finding grouped by
artifact with its severity, location, message, and concrete fix.
"""

from __future__ import annotations

from html import escape
from pathlib import Path

from ..model import ReviewResult, Severity

_SEV_COLOR = {
    Severity.CRITICAL: "#b00020",
    Severity.HIGH: "#d32f2f",
    Severity.MEDIUM: "#f9a825",
    Severity.LOW: "#0288d1",
    Severity.INFO: "#757575",
}
_SEV_ORDER = {s: i for i, s in enumerate([
    Severity.CRITICAL, Severity.HIGH, Severity.MEDIUM, Severity.LOW, Severity.INFO
])}


def _score_color(score: float, fail_under: float) -> str:
    if score < fail_under:
        return "#d32f2f"
    if score < 85:
        return "#f9a825"
    return "#2e7d32"


def _badge(sev: Severity) -> str:
    return (
        f'<span class="badge" style="background:{_SEV_COLOR[sev]}">'
        f'{escape(sev.value.upper())}</span>'
    )


def _finding_row(f, name: str) -> str:
    loc = f":{f.line}" if f.line else ""
    pid = f' <code>{escape(f.pitfall_id)}</code>' if f.pitfall_id else ""
    return (
        '<div class="finding">'
        f'<div class="fhead">{_badge(f.severity)} '
        f'<span class="dim">{escape(f.dimension.value)}</span>{pid} '
        f'<span class="loc">{escape(name)}{loc}</span></div>'
        f'<div class="msg">{escape(f.message)}</div>'
        f'<div class="fix"><b>Fix:</b> {escape(f.suggestion)}</div>'
        '</div>'
    )


def render(result: ReviewResult, fail_under: float = 70.0) -> str:
    overall = result.overall
    color = _score_color(overall, fail_under)
    status = "PASS" if overall >= fail_under else "FAIL"

    parts: list[str] = []
    parts.append("<!doctype html><html lang='en'><head><meta charset='utf-8'>")
    parts.append("<meta name='viewport' content='width=device-width, initial-scale=1'>")
    parts.append("<title>sddreview report</title>")
    parts.append("""<style>
:root{font-family:-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;line-height:1.45}
body{margin:0;background:#f6f7f9;color:#1b1f24}
.wrap{max-width:920px;margin:0 auto;padding:28px}
.card{background:#fff;border:1px solid #e4e7eb;border-radius:10px;padding:20px;margin:0 0 18px}
.score{font-size:46px;font-weight:700;line-height:1}
.muted{color:#6b7280;font-size:13px}
.coverage{border-left:4px solid #f9a825;background:#fffaf0;padding:10px 14px;border-radius:6px;margin-top:12px;font-size:14px}
.coverage.ok{border-color:#2e7d32;background:#f3faf4}
table{width:100%;border-collapse:collapse;font-size:14px}
th,td{text-align:left;padding:8px 10px;border-bottom:1px solid #eef0f2}
th{color:#6b7280;font-weight:600}
td.num{text-align:right;font-variant-numeric:tabular-nums}
.badge{color:#fff;font-size:11px;font-weight:700;padding:2px 7px;border-radius:999px}
.finding{border:1px solid #eef0f2;border-radius:8px;padding:12px 14px;margin:10px 0;background:#fff}
.fhead{display:flex;gap:8px;align-items:center;flex-wrap:wrap;font-size:13px}
.dim{color:#6b7280}
.loc{margin-left:auto;color:#9aa3ad;font-size:12px}
.msg{margin:6px 0 4px;font-weight:500}
.fix{color:#1f6f3c;font-size:14px}
code{background:#eef0f2;padding:1px 5px;border-radius:4px;font-size:12px}
h1{font-size:20px;margin:0 0 4px}h2{font-size:16px;margin:22px 0 8px}
ol{padding-left:20px}ol li{margin:6px 0}
.foot{color:#9aa3ad;font-size:12px;text-align:center;margin-top:8px}
</style></head><body><div class='wrap'>""")

    # Header card.
    parts.append("<div class='card'>")
    parts.append("<h1>SDD Review Report</h1>")
    parts.append(
        f"<div class='muted'>tool <b>{escape(result.tool)}</b> · "
        f"engine <b>{escape(result.engine)}</b> · "
        f"coverage <b>{escape(result.coverage)}</b>"
        + (f" · {escape(result.timestamp)}" if result.timestamp else "")
        + "</div>"
    )
    parts.append(
        f"<div style='margin-top:14px'><span class='score' style='color:{color}'>"
        f"{overall:.1f}</span> <span class='muted'>/100 · {status} "
        f"(threshold {fail_under:.0f})</span></div>"
    )
    cov_cls = "coverage ok" if result.judge_used else "coverage"
    parts.append(f"<div class='{cov_cls}'>{escape(result.coverage_note)}</div>")
    parts.append("</div>")

    # Summary table.
    parts.append("<div class='card'><h2 style='margin-top:0'>Artifacts</h2>")
    parts.append("<table><tr><th>Artifact</th><th>Type</th><th class='num'>Score</th>"
                 "<th class='num'>Findings</th></tr>")
    for a in result.artifacts:
        parts.append(
            f"<tr><td>{escape(Path(a.path).name)}</td><td>{escape(a.type.value)}</td>"
            f"<td class='num'>{a.overall:.0f}</td><td class='num'>{len(a.findings)}</td></tr>"
        )
    parts.append("</table></div>")

    # Top fixes.
    top = result.prioritized_findings()[:5]
    if top:
        parts.append("<div class='card'><h2 style='margin-top:0'>Top fixes</h2><ol>")
        for f in top:
            name = Path(f.artifact_path).name if f.artifact_path else "?"
            loc = f":{f.line}" if f.line else ""
            parts.append(
                f"<li>{_badge(f.severity)} <b>{escape(name)}{loc}</b> — "
                f"{escape(f.message)}<br><span class='fix'>{escape(f.suggestion)}</span></li>"
            )
        parts.append("</ol></div>")

    # Findings per artifact.
    for a in result.artifacts:
        if not a.findings:
            continue
        parts.append(f"<div class='card'><h2 style='margin-top:0'>{escape(Path(a.path).name)} "
                     f"<span class='muted'>({a.overall:.0f}/100)</span></h2>")
        for f in sorted(a.findings, key=lambda x: _SEV_ORDER.get(x.severity, 9)):
            parts.append(_finding_row(f, Path(a.path).name))
        parts.append("</div>")

    if not result.all_findings:
        parts.append("<div class='card'>No findings. 🎉</div>")

    parts.append("<div class='foot'>Generated by sddreview</div>")
    parts.append("</div></body></html>")
    return "".join(parts)
