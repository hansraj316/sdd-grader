"""SARIF 2.1.0 output so findings surface in GitHub code scanning / PR annotations.

Each finding becomes a SARIF result; each distinct pitfall id becomes a SARIF rule, so
findings group and link by stable rule id in the GitHub Security tab.
"""

from __future__ import annotations

import json
from pathlib import Path

from ..catalog import load_catalog
from ..model import ReviewResult, Severity

SCHEMA = "https://json.schemastore.org/sarif-2.1.0.json"
GENERIC_RULE = "sddreview.finding"

# SARIF level per severity.
_LEVEL = {
    Severity.CRITICAL: "error",
    Severity.HIGH: "error",
    Severity.MEDIUM: "warning",
    Severity.LOW: "note",
    Severity.INFO: "note",
}


def _rule_id(pitfall_id: str | None) -> str:
    return pitfall_id or GENERIC_RULE


def _relativize(path: str | None, root: Path | None) -> str:
    if not path:
        return ""
    if root is None:
        return path
    try:
        return str(Path(path).resolve().relative_to(root.resolve()))
    except ValueError:
        return path


def render(result: ReviewResult, root: Path | None = None) -> str:
    catalog = load_catalog()
    findings = result.all_findings

    # One rule per distinct pitfall id present, plus the generic catch-all.
    rule_ids: list[str] = []
    seen: set[str] = set()
    for f in findings:
        rid = _rule_id(f.pitfall_id)
        if rid not in seen:
            seen.add(rid)
            rule_ids.append(rid)
    if GENERIC_RULE not in seen and findings:
        rule_ids.append(GENERIC_RULE)

    rules = []
    for rid in rule_ids:
        pit = catalog.get(rid)
        rules.append({
            "id": rid,
            "name": pit.name if pit else "SDD finding",
            "shortDescription": {"text": pit.name if pit else "Spec quality finding"},
            "fullDescription": {"text": pit.why if pit else "A spec-quality finding from sddreview."},
            "helpUri": "https://github.com/hansraj316/sddreview",
            "defaultConfiguration": {"level": _LEVEL[pit.severity] if pit else "warning"},
        })

    results = []
    for f in findings:
        location = {
            "physicalLocation": {
                "artifactLocation": {"uri": _relativize(f.artifact_path, root)},
            }
        }
        if f.line:
            location["physicalLocation"]["region"] = {"startLine": f.line}
        results.append({
            "ruleId": _rule_id(f.pitfall_id),
            "level": _LEVEL[f.severity],
            "message": {"text": f"{f.message} — fix: {f.suggestion}"},
            "locations": [location],
            "properties": {
                "dimension": f.dimension.value,
                "severity": f.severity.value,
                "suggestion": f.suggestion,
                "pitfall_id": f.pitfall_id,
                "source": f.source.value,
            },
        })

    doc = {
        "$schema": SCHEMA,
        "version": "2.1.0",
        "runs": [{
            "tool": {"driver": {
                "name": "sddreview",
                "informationUri": "https://github.com/hansraj316/sddreview",
                "rules": rules,
            }},
            "results": results,
        }],
    }
    return json.dumps(doc, indent=2)
