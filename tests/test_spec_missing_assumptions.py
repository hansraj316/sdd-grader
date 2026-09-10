"""Tests for SPEC-MISSING-ASSUMPTIONS lint check.

Fires when a spec has ≥3 FR-/NFR- requirement lines but no section heading
matching Assumptions / Constraints / Preconditions / Prerequisites /
Boundary Conditions (ISO/IEC/IEEE 29148:2018 §5.2.1, Canon Volere §6+§10).
"""
from __future__ import annotations

import pytest

from sddgrade.adapters.base import parse_sections
from sddgrade.catalog import load_catalog
from sddgrade.engine.lint import _spec_missing_assumptions
from sddgrade.model import Artifact, ArtifactType


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_spec(raw: str) -> Artifact:
    return Artifact(
        path="spec.md",
        type=ArtifactType.SPEC,
        raw=raw,
        sections=parse_sections(raw),
    )


def _make_plan(raw: str) -> Artifact:
    return Artifact(
        path="plan.md",
        type=ArtifactType.PLAN,
        raw=raw,
        sections=parse_sections(raw),
    )


CATALOG = load_catalog()


# ---------------------------------------------------------------------------
# FIRE cases — should detect SPEC-MISSING-ASSUMPTIONS
# ---------------------------------------------------------------------------

def test_three_fr_lines_no_assumptions_fires() -> None:
    """Spec with exactly 3 FR- lines and no assumptions/constraints heading → fires."""
    spec = _make_spec(
        "# Widget Service Spec\n\n"
        "## Problem Statement\n\nWe need a widget service.\n\n"
        "## Requirements\n\n"
        "- FR-001: The system shall process widgets within 200 ms.\n"
        "- FR-002: The system shall store up to 10 000 widgets.\n"
        "- FR-003: The system shall support concurrent access by 50 users.\n"
    )
    findings = _spec_missing_assumptions(spec, CATALOG)
    assert len(findings) == 1
    assert findings[0].pitfall_id == "SPEC-MISSING-ASSUMPTIONS"
    assert "assumption" in findings[0].message.lower() or "constraint" in findings[0].message.lower()


def test_mixed_fr_nfr_no_constraints_fires() -> None:
    """Spec with FR- and NFR- lines but no constraints heading → fires."""
    spec = _make_spec(
        "# Payment API Spec\n\n"
        "## Motivation\n\nEnable payment processing.\n\n"
        "## Glossary\n\n- Widget: a billable unit.\n\n"
        "## Requirements\n\n"
        "- FR-001: The system shall process payments.\n"
        "- FR-002: The system shall validate card numbers per PCI-DSS.\n"
        "- FR-003: The system shall generate receipts.\n"
        "- NFR-001: The API shall respond within 500 ms at the 95th percentile.\n"
    )
    findings = _spec_missing_assumptions(spec, CATALOG)
    assert len(findings) == 1
    assert findings[0].pitfall_id == "SPEC-MISSING-ASSUMPTIONS"


def test_five_fr_lines_fires_exactly_once() -> None:
    """Spec with 5 FR- lines and no assumptions heading → fires exactly once."""
    spec = _make_spec(
        "# Reporting Spec\n\n"
        "## Out of Scope\n\nExporting to Excel is out of scope.\n\n"
        "## Requirements\n\n"
        "- FR-001: The system shall generate PDF reports.\n"
        "- FR-002: The system shall schedule weekly exports.\n"
        "- FR-003: The system shall email reports to subscribers.\n"
        "- FR-004: The system shall support filtering by date range.\n"
        "- FR-005: The system shall archive reports older than 90 days.\n"
    )
    findings = _spec_missing_assumptions(spec, CATALOG)
    assert len(findings) == 1, "Should fire exactly once regardless of FR count"
    assert findings[0].pitfall_id == "SPEC-MISSING-ASSUMPTIONS"
    assert findings[0].line == 1


# ---------------------------------------------------------------------------
# SILENT cases — must NOT fire SPEC-MISSING-ASSUMPTIONS
# ---------------------------------------------------------------------------

def test_assumptions_heading_silences() -> None:
    """'## Assumptions' heading → silent."""
    spec = _make_spec(
        "# Service Spec\n\n"
        "## Requirements\n\n"
        "- FR-001: The system shall provide login.\n"
        "- FR-002: The system shall maintain sessions.\n"
        "- FR-003: The system shall log out users after timeout.\n\n"
        "## Assumptions\n\n"
        "- Users have a modern browser.\n"
        "- The server runs on Linux Ubuntu 22.04 LTS.\n"
    )
    findings = _spec_missing_assumptions(spec, CATALOG)
    assert findings == [], "Assumptions heading should silence the check"


def test_constraints_heading_silences() -> None:
    """'## Constraints' heading → silent."""
    spec = _make_spec(
        "# Mobile App Spec\n\n"
        "## Requirements\n\n"
        "- FR-001: The app shall display a dashboard.\n"
        "- FR-002: The app shall sync data every 60 s.\n"
        "- FR-003: The app shall work offline.\n\n"
        "## Constraints\n\n"
        "- Must support iOS 15+ and Android 11+.\n"
        "- App size shall not exceed 50 MB.\n"
    )
    findings = _spec_missing_assumptions(spec, CATALOG)
    assert findings == [], "Constraints heading should silence the check"


def test_preconditions_heading_silences() -> None:
    """'## Preconditions' heading → silent."""
    spec = _make_spec(
        "# Checkout Spec\n\n"
        "## Requirements\n\n"
        "- FR-001: The user shall be able to add items to the cart.\n"
        "- FR-002: The system shall calculate tax.\n"
        "- FR-003: The system shall confirm the order.\n\n"
        "## Preconditions\n\n"
        "- The user must be authenticated.\n"
        "- Payment gateway credentials must be configured.\n"
    )
    findings = _spec_missing_assumptions(spec, CATALOG)
    assert findings == [], "Preconditions heading should silence the check"


def test_prerequisites_heading_silences() -> None:
    """'## Prerequisites' heading → silent."""
    spec = _make_spec(
        "# Deployment Spec\n\n"
        "## Requirements\n\n"
        "- FR-001: The system shall deploy to Kubernetes.\n"
        "- FR-002: The system shall expose a health-check endpoint.\n"
        "- FR-003: The system shall log to stdout.\n\n"
        "## Prerequisites\n\n"
        "- Kubernetes cluster v1.28+ must be available.\n"
        "- Docker image registry must be configured.\n"
    )
    findings = _spec_missing_assumptions(spec, CATALOG)
    assert findings == [], "Prerequisites heading should silence the check"


def test_boundary_conditions_heading_silences() -> None:
    """'## Boundary Conditions' heading → silent."""
    spec = _make_spec(
        "# Search Service Spec\n\n"
        "## Requirements\n\n"
        "- FR-001: The search shall return results within 300 ms.\n"
        "- FR-002: The search shall handle UTF-8 input.\n"
        "- FR-003: The search shall rank by relevance score.\n\n"
        "## Boundary Conditions\n\n"
        "- Maximum query length: 500 characters.\n"
        "- Maximum results per page: 100.\n"
    )
    findings = _spec_missing_assumptions(spec, CATALOG)
    assert findings == [], "Boundary Conditions heading should silence the check"


def test_dependencies_and_constraints_heading_silences() -> None:
    """'## Dependencies and Constraints' heading → silent."""
    spec = _make_spec(
        "# Integration Spec\n\n"
        "## Requirements\n\n"
        "- FR-001: The service shall call the payment API.\n"
        "- FR-002: The service shall retry on transient failures.\n"
        "- FR-003: The service shall emit events on success.\n\n"
        "## Dependencies and Constraints\n\n"
        "- Payment API v3.0+ required.\n"
        "- Events must be published within 2 s of completion.\n"
    )
    findings = _spec_missing_assumptions(spec, CATALOG)
    assert findings == [], "Dependencies and Constraints heading should silence the check"


def test_fewer_than_3_fr_lines_silent() -> None:
    """Spec with only 2 FR- lines does not reach guard threshold → silent."""
    spec = _make_spec(
        "# Tiny Spec\n\n"
        "## Requirements\n\n"
        "- FR-001: The system shall support login.\n"
        "- FR-002: The system shall support logout.\n"
    )
    findings = _spec_missing_assumptions(spec, CATALOG)
    assert findings == [], "Spec with < 3 FR- lines should not fire"


def test_plan_artifact_skipped() -> None:
    """Plan artifact should not trigger SPEC-MISSING-ASSUMPTIONS."""
    plan = _make_plan(
        "# Deploy Plan\n\n"
        "## Requirements\n\n"
        "- FR-001: Deploy to AWS.\n"
        "- FR-002: Use RDS for storage.\n"
        "- FR-003: Enable CloudWatch monitoring.\n"
    )
    findings = _spec_missing_assumptions(plan, CATALOG)
    assert findings == [], "Plan artifact should be skipped"


def test_fenced_frs_not_counted() -> None:
    """FR- IDs inside a fenced code block do not count toward the guard threshold."""
    spec = _make_spec(
        "# Code Spec\n\n"
        "## Requirements\n\n"
        "Here are some requirements:\n\n"
        "```\n"
        "- FR-001: inside a fence\n"
        "- FR-002: inside a fence\n"
        "- FR-003: inside a fence\n"
        "- FR-004: inside a fence\n"
        "```\n\n"
        "Only prose below.\n"
    )
    findings = _spec_missing_assumptions(spec, CATALOG)
    assert findings == [], "Fenced FR- lines should not trigger the guard"


def test_assumptions_and_constraints_compound_heading_silences() -> None:
    """'## Assumptions and Constraints' heading → silent."""
    spec = _make_spec(
        "# API Spec\n\n"
        "## Requirements\n\n"
        "- FR-001: The API shall authenticate via OAuth 2.0.\n"
        "- FR-002: The API shall rate-limit requests to 100 per minute.\n"
        "- FR-003: The API shall version all endpoints.\n\n"
        "## Assumptions and Constraints\n\n"
        "- OAuth provider must be Google or Microsoft.\n"
        "- API must remain backward-compatible for 2 major versions.\n"
    )
    findings = _spec_missing_assumptions(spec, CATALOG)
    assert findings == [], "Assumptions and Constraints compound heading should silence the check"
