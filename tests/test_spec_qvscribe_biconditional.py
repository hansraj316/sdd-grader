"""Tests for SPEC-QVSCRIBE-BICONDITIONAL pitfall.

Fires when normative requirement lines (shall/must or FR-/NFR- identifier) in a
Requirements/Acceptance section contain the exact phrase 'if and only if'.

A biconditional creates two implicit test obligations (A→B and B→A).  Testers
routinely verify only the forward direction; the reverse is silently skipped.

Sources:
  - QVscribe Level-1 Clarity defect 'Ambiguous Logic'
  - ISO/IEC/IEEE 29148:2018 §5.2.5(a): requirement must be unambiguous
"""

from __future__ import annotations

import pytest

from sddgrade.adapters.base import parse_sections
from sddgrade.catalog import load_catalog
from sddgrade.engine.lint import _spec_qvscribe_biconditional
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


def test_shall_if_and_only_if_fires() -> None:
    """'if and only if' on a SHALL requirement line → fires."""
    spec = _make_spec(
        "# Feature Spec\n\n"
        "## Requirements\n\n"
        "- FR-005: The system shall grant admin access if and only if the user holds both "
        "the 'admin' role and an active MFA session.\n"
    )
    findings = _spec_qvscribe_biconditional(spec, CATALOG)
    assert len(findings) == 1
    assert findings[0].pitfall_id == "SPEC-QVSCRIBE-BICONDITIONAL"
    assert "if and only if" in findings[0].message.lower() or "biconditional" in findings[0].message.lower()


def test_must_if_and_only_if_fires() -> None:
    """'if and only if' on a MUST requirement line → fires."""
    spec = _make_spec(
        "# Spec\n\n"
        "## Requirements\n\n"
        "- NFR-002: The cache must be invalidated if and only if the underlying data changes.\n"
    )
    findings = _spec_qvscribe_biconditional(spec, CATALOG)
    assert len(findings) == 1
    assert findings[0].pitfall_id == "SPEC-QVSCRIBE-BICONDITIONAL"


def test_fr_identifier_if_and_only_if_fires() -> None:
    """'if and only if' on a line with an FR- identifier → fires."""
    spec = _make_spec(
        "# Spec\n\n"
        "## Requirements\n\n"
        "FR-010 The alert shall fire if and only if three consecutive health checks fail.\n"
    )
    findings = _spec_qvscribe_biconditional(spec, CATALOG)
    assert len(findings) == 1


def test_case_insensitive_IF_AND_ONLY_IF_fires() -> None:
    """'IF AND ONLY IF' in uppercase on a SHALL line → fires (case-insensitive)."""
    spec = _make_spec(
        "# Spec\n\n"
        "## Requirements\n\n"
        "- FR-003: The gateway shall forward the request IF AND ONLY IF the token is valid.\n"
    )
    findings = _spec_qvscribe_biconditional(spec, CATALOG)
    assert len(findings) == 1


def test_multiple_violations_aggregate_single_finding() -> None:
    """Two requirement lines with 'if and only if' → single aggregate finding at first line."""
    spec = _make_spec(
        "# Spec\n\n"
        "## Requirements\n\n"
        "- FR-001: The system shall grant access if and only if the user is authenticated.\n"
        "- FR-002: The API shall return 200 if and only if the payload is valid.\n"
        "- FR-003: The system shall validate all submitted forms.\n"
    )
    findings = _spec_qvscribe_biconditional(spec, CATALOG)
    assert len(findings) == 1
    assert "2 requirement line" in findings[0].message
    assert findings[0].line == 5  # first offending line (1-indexed)


def test_nfr_identifier_if_and_only_if_fires() -> None:
    """'if and only if' on a line with an NFR- identifier → fires."""
    spec = _make_spec(
        "# Spec\n\n"
        "## Non-Functional Requirements\n\n"
        "- NFR-001: Backups shall run if and only if disk usage exceeds 80%.\n"
    )
    findings = _spec_qvscribe_biconditional(spec, CATALOG)
    assert len(findings) == 1


def test_mixed_case_If_And_Only_If_fires() -> None:
    """Title-case 'If And Only If' → fires."""
    spec = _make_spec(
        "# Spec\n\n"
        "## Acceptance Criteria\n\n"
        "- AC-001: The report shall be sent If And Only If all validations pass.\n"
    )
    findings = _spec_qvscribe_biconditional(spec, CATALOG)
    assert len(findings) == 1


# ---------------------------------------------------------------------------
# SILENT cases — check should NOT trigger
# ---------------------------------------------------------------------------


def test_no_biconditional_is_silent() -> None:
    """Requirements without 'if and only if' → silent."""
    spec = _make_spec(
        "# Spec\n\n"
        "## Requirements\n\n"
        "- FR-001: The system shall validate all submitted forms.\n"
        "- FR-002: The API must respond within 200 ms.\n"
        "- NFR-001: The service shall support 500 concurrent users.\n"
    )
    findings = _spec_qvscribe_biconditional(spec, CATALOG)
    assert findings == []


def test_plain_if_without_and_only_is_silent() -> None:
    """A simple conditional 'if' on a SHALL line → silent (not a biconditional)."""
    spec = _make_spec(
        "# Spec\n\n"
        "## Requirements\n\n"
        "- FR-001: The system shall send an alert if the threshold is exceeded.\n"
    )
    findings = _spec_qvscribe_biconditional(spec, CATALOG)
    assert findings == []


def test_biconditional_in_fenced_block_is_silent() -> None:
    """'if and only if' inside a fenced code block → silent."""
    spec = _make_spec(
        "# Spec\n\n"
        "## Requirements\n\n"
        "- FR-001: The API must respond within 200 ms.\n\n"
        "```python\n"
        "# grant access if and only if role is admin\n"
        "if user.role == 'admin' and user.mfa_active:\n"
        "    grant_access()\n"
        "```\n"
    )
    findings = _spec_qvscribe_biconditional(spec, CATALOG)
    assert findings == []


def test_biconditional_in_prose_without_modal_is_silent() -> None:
    """'if and only if' in a prose paragraph (no shall/must, no FR-/NFR- id) → silent."""
    spec = _make_spec(
        "# Spec\n\n"
        "## Background\n\n"
        "Access is conceptually granted if and only if both conditions hold, but the "
        "exact conditions are defined in the security model.\n\n"
        "## Requirements\n\n"
        "- FR-001: The system shall validate all submitted forms.\n"
    )
    findings = _spec_qvscribe_biconditional(spec, CATALOG)
    assert findings == []


def test_plan_artifact_is_silent() -> None:
    """Pitfall applies only to spec → plan artifact is silent."""
    plan = Artifact(
        path="plan.md",
        type=ArtifactType.PLAN,
        raw=(
            "# Plan\n\n"
            "## Deployment\n\n"
            "- FR-001: The service shall deploy if and only if CI is green.\n"
        ),
        sections=parse_sections(
            "# Plan\n\n"
            "## Deployment\n\n"
            "- FR-001: The service shall deploy if and only if CI is green.\n"
        ),
    )
    findings = _spec_qvscribe_biconditional(plan, CATALOG)
    assert findings == []


def test_only_if_without_and_is_silent() -> None:
    """'only if' (missing 'and') on a SHALL line → silent (incomplete biconditional phrase)."""
    spec = _make_spec(
        "# Spec\n\n"
        "## Requirements\n\n"
        "- FR-001: The system shall retry only if the error is transient.\n"
    )
    findings = _spec_qvscribe_biconditional(spec, CATALOG)
    assert findings == []
