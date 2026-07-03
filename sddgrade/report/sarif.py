"""SARIF 2.1.0 output so findings surface in GitHub code scanning / PR annotations.

Each finding becomes a SARIF result; each distinct pitfall id becomes a SARIF rule, so
findings group and link by stable rule id in the GitHub Security tab.

Robustness (#66): artifact URIs are always POSIX-style repo-relative paths; findings
whose path is missing or falls outside the repo root get no ``locations`` at all
(GitHub rejects uploads with an empty/unmappable URI rather than skipping them). Each
result carries a ``partialFingerprints`` entry (ruleId + relative path) so alert
identity survives message rewording, and rule default levels come from the same
severity→level mapping as the per-result levels.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from ..catalog import load_catalog
from ..model import Finding, ReviewResult, Severity
from .common import SARIF_LEVEL

SCHEMA = "https://json.schemastore.org/sarif-2.1.0.json"
GENERIC_RULE = "sddgrade.finding"


def _rule_id(pitfall_id: str | None) -> str:
    return pitfall_id or GENERIC_RULE


def _relativize(path: str | None, root: Path | None) -> str | None:
    """Repo-relative POSIX URI for ``path``, or None when no valid one exists.

    None (rather than "" or an absolute/backslash path) tells the caller to omit
    the location entirely — an empty or unmappable URI breaks the GitHub upload.
    """
    if not path:
        return None
    try:
        p = Path(path)
        if root is None:
            return p.as_posix() if not p.is_absolute() else None
        return p.resolve().relative_to(root.resolve()).as_posix()
    except (ValueError, OSError):
        return None


def _fingerprint(rule_id: str, uri: str | None) -> str:
    """Stable alert identity: rule + file, independent of message wording."""
    return hashlib.sha256(f"{rule_id}:{uri or ''}".encode("utf-8")).hexdigest()[:32]


def _result_level(f: Finding) -> str:
    return SARIF_LEVEL[f.severity]


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

    # Rule default level: the most severe level actually emitted for that rule in
    # this run (same SARIF_LEVEL mapping as per-result levels), falling back to the
    # catalog severity — so the Security-tab severity filter never disagrees with
    # the results themselves.
    max_sev_by_rule: dict[str, Severity] = {}
    sev_rank = {s: i for i, s in enumerate(Severity)}  # INFO..CRITICAL ascending
    for f in findings:
        rid = _rule_id(f.pitfall_id)
        cur = max_sev_by_rule.get(rid)
        if cur is None or sev_rank[f.severity] > sev_rank[cur]:
            max_sev_by_rule[rid] = f.severity

    rules = []
    for rid in rule_ids:
        pit = catalog.get(rid)
        sev = max_sev_by_rule.get(rid) or (pit.severity if pit else None)
        rules.append({
            "id": rid,
            "name": pit.name if pit else "SDD finding",
            "shortDescription": {"text": pit.name if pit else "Spec quality finding"},
            "fullDescription": {"text": pit.why if pit else "A spec-quality finding from sddgrade."},
            "helpUri": "https://github.com/hansraj316/sdd-grader",
            "defaultConfiguration": {"level": SARIF_LEVEL[sev] if sev else "warning"},
        })

    results = []
    for f in findings:
        rid = _rule_id(f.pitfall_id)
        uri = _relativize(f.artifact_path, root)
        entry = {
            "ruleId": rid,
            "level": _result_level(f),
            "message": {"text": f"{f.message} — fix: {f.suggestion}"},
            "partialFingerprints": {"sddgradeFingerprint/v1": _fingerprint(rid, uri)},
            "properties": {
                "dimension": f.dimension.value,
                "severity": f.severity.value,
                "suggestion": f.suggestion,
                "pitfall_id": f.pitfall_id,
                "source": f.source.value,
            },
        }
        if uri is not None:
            location = {"physicalLocation": {"artifactLocation": {"uri": uri}}}
            if f.line:
                location["physicalLocation"]["region"] = {"startLine": f.line}
            entry["locations"] = [location]
        results.append(entry)

    doc = {
        "$schema": SCHEMA,
        "version": "2.1.0",
        "runs": [{
            "tool": {"driver": {
                "name": "sddgrade",
                "informationUri": "https://github.com/hansraj316/sdd-grader",
                "rules": rules,
            }},
            "results": results,
        }],
    }
    return json.dumps(doc, indent=2)
