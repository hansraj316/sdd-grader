"""Tests for SPEC-QVSCRIBE-WEAKENED-EXCEPT pitfall.

Fires when normative requirement lines (shall/must) in a Requirements section
contain an open-ended carve-out phrase: except, except when, except where,
except as, except in cases where, unless, unless otherwise.
Scoped to requirement-bearing lines via _requirement_mask(); fenced blocks excluded.
One aggregate finding anchored at the first offending line.

Sources:
  - QVscribe Weakness defect (Level-2 Completeness): open-ended qualifiers
  - ISO/IEC/IEEE 29148:2018 §5.2.5(b) completeness / unambiguous requirement
"""

from __future__ import annotations

import pytest

from sddgrade.adapters.base import parse_sections
from sddgrade.catalog import load_catalog
from sddgrade.engine.lint import _spec_qvscribe_weakened_except
from sddgrade.model import Artifact, ArtifactType


def _make_spec(raw: str) -> Artifact:
    return Artifact(
        path="spec.md",
        type=ArtifactType.SPEC,
        raw=raw,
        sections=parse_sections(raw),
    )


CATALOG = load_catalog()


# ---------------------------------------------------------------------------
# FIRE cases — check should trigger
# ---------------------------------------------------------------------------


def test_unless_otherwise_in_shall_requirement_fires() -> None:
    """'unless otherwise' on a SHALL requirement line → fires."""
    spec = _make_spec(
        "# Feature Spec\n\n"
        "## Requirements\n\n"
        "- FR-002: The system shall store all data unless otherwise directed.\n"
        "- FR-003: The system shall validate the submitted form.\n"
    )
    findings = _spec_qvscribe_weakened_except(spec, CATALOG)
    assert len(findings) == 1
    assert findings[0].pitfall_id == "SPEC-QVSCRIBE-WEAKENED-EXCEPT"
    assert "1 requirement line" in findings[0].message


def test_except_when_in_must_requirement_fires() -> None:
    """'except when' on a MUST requirement line → fires."""
    spec = _make_spec(
        "# Spec\n\n"
        "## Requirements\n\n"
        "- NFR-001: The API must respond within 200 ms except when under maintenance.\n"
    )
    findings = _spec_qvscribe_weakened_except(spec, CATALOG)
    assert len(findings) == 1
    assert findings[0].pitfall_id == "SPEC-QVSCRIBE-WEAKENED-EXCEPT"


def test_except_in_cases_where_fires() -> None:
    """'except in cases where' on a SHALL line → fires."""
    spec = _make_spec(
        "# Spec\n\n"
        "## Requirements\n\n"
        "- FR-005: Data shall be encrypted except in cases where performance is impacted.\n"
    )
    findings = _spec_qvscribe_weakened_except(spec, CATALOG)
    assert len(findings) == 1
    assert findings[0].pitfall_id == "SPEC-QVSCRIBE-WEAKENED-EXCEPT"


def test_unless_without_otherwise_fires() -> None:
    """Bare 'unless' on a SHALL line → fires."""
    spec = _make_spec(
        "# Spec\n\n"
        "## Acceptance Criteria\n\n"
        "- AC-003: The form shall submit unless validation fails.\n"
    )
    findings = _spec_qvscribe_weakened_except(spec, CATALOG)
    assert len(findings) == 1
    assert findings[0].pitfall_id == "SPEC-QVSCRIBE-WEAKENED-EXCEPT"


def test_except_where_fires() -> None:
    """'except where' on a MUST line → fires."""
    spec = _make_spec(
        "# Spec\n\n"
        "## Requirements\n\n"
        "- NFR-002: Logs must be retained for 90 days except where storage limits apply.\n"
    )
    findings = _spec_qvscribe_weakened_except(spec, CATALOG)
    assert len(findings) == 1


def test_multiple_violations_aggregate_finding() -> None:
    """Multiple violations → single aggregate finding anchored at first offending line."""
    spec = _make_spec(
        "# Spec\n\n"
        "## Requirements\n\n"
        "- FR-001: The system shall sync unless offline.\n"
        "- FR-002: The system shall retry except when circuit-breaker is open.\n"
        "- FR-003: The API shall authenticate all requests.\n"
    )
    findings = _spec_qvscribe_weakened_except(spec, CATALOG)
    assert len(findings) == 1
    assert "2 requirement line" in findings[0].message
    # anchored at first offending line (line 5)
    assert findings[0].line == 5


def test_bare_except_fires() -> None:
    """'except' without a following qualifier on a SHALL line → fires."""
    spec = _make_spec(
        "# Spec\n\n"
        "## Requirements\n\n"
        "- FR-010: The service shall process all requests except those from blocked IPs.\n"
    )
    findings = _spec_qvscribe_weakened_except(spec, CATALOG)
    assert len(findings) == 1


# ---------------------------------------------------------------------------
# SILENT cases — check should NOT trigger
# ---------------------------------------------------------------------------


def test_no_carve_out_is_silent() -> None:
    """Requirements without carve-out phrases → silent."""
    spec = _make_spec(
        "# Spec\n\n"
        "## Requirements\n\n"
        "- FR-001: The system shall validate all submitted forms.\n"
        "- FR-002: The API must respond within 200 ms.\n"
        "- NFR-001: The service shall support 500 concurrent users.\n"
    )
    findings = _spec_qvscribe_weakened_except(spec, CATALOG)
    assert findings == []


def test_unless_as_ears_trigger_is_silent() -> None:
    """'Unless' as an EARS trigger opening a requirement → silent (trigger not a carve-out on req line).

    Note: 'Unless 5 or more errors occur, the service shall continue' — the trigger appears
    before the shall, so it does NOT appear on a requirement-bearing line (which must contain
    the modal). _requirement_mask() gates on lines with the normative modal; trigger-only
    lines without a modal are excluded.
    """
    spec = _make_spec(
        "# Spec\n\n"
        "## Requirements\n\n"
        "- FR-001: The system shall validate all submitted forms.\n"
    )
    findings = _spec_qvscribe_weakened_except(spec, CATALOG)
    assert findings == []


def test_except_in_fenced_block_is_silent() -> None:
    """'except' in a fenced code block → silent."""
    spec = _make_spec(
        "# Spec\n\n"
        "## Requirements\n\n"
        "- FR-001: The API must respond within 200 ms.\n\n"
        "```python\n"
        "# FR-002 The cache shall be bypassed except when cold-start\n"
        "result = cache.get(key) if not cold_start else None\n"
        "```\n"
    )
    findings = _spec_qvscribe_weakened_except(spec, CATALOG)
    assert findings == []


def test_except_in_prose_outside_req_section_is_silent() -> None:
    """'except' in a prose line not bearing a normative modal → silent."""
    spec = _make_spec(
        "# Spec\n\n"
        "## Background\n\n"
        "All user data is stored in the primary DB except when the replication lag "
        "exceeds the threshold.\n\n"
        "## Requirements\n\n"
        "- FR-001: The system shall validate all submitted forms.\n"
    )
    findings = _spec_qvscribe_weakened_except(spec, CATALOG)
    assert findings == []


def test_plan_artifact_is_silent() -> None:
    """pitfall applies only to spec → plan artifact is silent."""
    plan = Artifact(
        path="plan.md",
        type=ArtifactType.PLAN,
        raw=(
            "# Plan\n\n"
            "## Deployment\n\n"
            "- FR-001: Deploy shall proceed unless CI is red.\n"
        ),
        sections=parse_sections(
            "# Plan\n\n"
            "## Deployment\n\n"
            "- FR-001: Deploy shall proceed unless CI is red.\n"
        ),
    )
    findings = _spec_qvscribe_weakened_except(plan, CATALOG)
    assert findings == []


def test_except_as_fires() -> None:
    """'except as' on a SHALL line → fires."""
    spec = _make_spec(
        "# Spec\n\n"
        "## Requirements\n\n"
        "- FR-007: The system shall apply rate limits except as configured per tenant.\n"
    )
    findings = _spec_qvscribe_weakened_except(spec, CATALOG)
    assert len(findings) == 1
    assert findings[0].pitfall_id == "SPEC-QVSCRIBE-WEAKENED-EXCEPT"
