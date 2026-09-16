"""Tests for SPEC-MISSING-STAKEHOLDER lint check.

Fires when a spec has ≥3 FR-/NFR- requirement lines but no section heading
matching Stakeholders / User Roles / Personas / Actors / User Types
(ISO/IEC/IEEE 29148:2018 §5.1.2, Amazon Kiro spec template, AIDE).
"""
from __future__ import annotations

import pytest

from sddgrade.adapters.base import parse_sections
from sddgrade.catalog import load_catalog
from sddgrade.engine.lint import _spec_missing_stakeholder
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


def _make_tasks(raw: str) -> Artifact:
    return Artifact(
        path="tasks.md",
        type=ArtifactType.TASKS,
        raw=raw,
        sections=parse_sections(raw),
    )


CATALOG = load_catalog()


# ---------------------------------------------------------------------------
# FIRE cases — should detect SPEC-MISSING-STAKEHOLDER
# ---------------------------------------------------------------------------

def test_three_fr_lines_no_stakeholder_section_fires() -> None:
    """Spec with exactly 3 FR- lines and no stakeholder heading → fires."""
    spec = _make_spec(
        "# Widget Service Spec\n\n"
        "## Problem Statement\n\nWe need a widget service.\n\n"
        "## Requirements\n\n"
        "- FR-001: The system shall process widgets within 200 ms.\n"
        "- FR-002: The system shall store up to 10 000 widgets.\n"
        "- FR-003: The system shall support concurrent access by 50 users.\n"
    )
    findings = _spec_missing_stakeholder(spec, CATALOG)
    assert len(findings) == 1
    assert findings[0].pitfall_id == "SPEC-MISSING-STAKEHOLDER"
    assert "stakeholder" in findings[0].message.lower()


def test_five_fr_lines_no_stakeholder_fires_exactly_once() -> None:
    """Spec with 5 FR- lines and no stakeholder heading → fires exactly once."""
    spec = _make_spec(
        "# Reporting Spec\n\n"
        "## Motivation\n\nEnable reporting.\n\n"
        "## Assumptions\n\nThe reporting pipeline is already in place.\n\n"
        "## Requirements\n\n"
        "- FR-001: The system shall generate PDF reports.\n"
        "- FR-002: The system shall schedule weekly exports.\n"
        "- FR-003: The system shall email reports to subscribers.\n"
        "- FR-004: The system shall support filtering by date range.\n"
        "- FR-005: The system shall archive reports older than 90 days.\n"
    )
    findings = _spec_missing_stakeholder(spec, CATALOG)
    assert len(findings) == 1, "Should fire exactly once regardless of FR count"
    assert findings[0].pitfall_id == "SPEC-MISSING-STAKEHOLDER"
    assert findings[0].line == 1


def test_mixed_fr_nfr_no_stakeholder_fires() -> None:
    """Spec with FR- and NFR- lines but no stakeholder heading → fires."""
    spec = _make_spec(
        "# Payment API Spec\n\n"
        "## Motivation\n\nEnable payment processing.\n\n"
        "## Glossary\n\n- Widget: a billable unit.\n\n"
        "## Requirements\n\n"
        "- FR-001: The system shall process payments.\n"
        "- FR-002: The system shall validate card numbers per PCI-DSS.\n"
        "- NFR-001: The API shall respond within 500 ms at the 95th percentile.\n"
    )
    findings = _spec_missing_stakeholder(spec, CATALOG)
    assert len(findings) == 1
    assert findings[0].pitfall_id == "SPEC-MISSING-STAKEHOLDER"


def test_no_stakeholder_heading_among_many_sections_fires() -> None:
    """Spec with many sections but none being stakeholder-related → fires."""
    spec = _make_spec(
        "# Order Service Spec\n\n"
        "## Overview\n\nThis spec covers order management.\n\n"
        "## Out of Scope\n\nRefunds are out of scope.\n\n"
        "## Assumptions\n\nPayment gateway is available.\n\n"
        "## Requirements\n\n"
        "- FR-001: The system shall accept orders.\n"
        "- FR-002: The system shall validate order items.\n"
        "- FR-003: The system shall notify users on order status change.\n"
        "- NFR-001: Order creation must complete within 2 seconds.\n"
    )
    findings = _spec_missing_stakeholder(spec, CATALOG)
    assert len(findings) == 1
    assert findings[0].pitfall_id == "SPEC-MISSING-STAKEHOLDER"


# ---------------------------------------------------------------------------
# SILENT cases — must NOT fire SPEC-MISSING-STAKEHOLDER
# ---------------------------------------------------------------------------

def test_stakeholders_heading_silences() -> None:
    """Spec with ## Stakeholders heading → silent."""
    spec = _make_spec(
        "# Auth Service Spec\n\n"
        "## Stakeholders\n\n"
        "- End User: logs in and resets password.\n"
        "- Admin: manages user accounts.\n\n"
        "## Requirements\n\n"
        "- FR-001: The system shall support OAuth 2.0 login.\n"
        "- FR-002: The system shall lock accounts after 5 failed attempts.\n"
        "- FR-003: The system shall email password-reset links.\n"
    )
    findings = _spec_missing_stakeholder(spec, CATALOG)
    assert findings == []


def test_user_roles_heading_silences() -> None:
    """Spec with ## User Roles heading → silent."""
    spec = _make_spec(
        "# Inventory Spec\n\n"
        "## User Roles\n\n"
        "- Warehouse Manager: views and updates stock levels.\n"
        "- Auditor: reads-only inventory history.\n\n"
        "## Requirements\n\n"
        "- FR-001: The system shall display current stock levels.\n"
        "- FR-002: The system shall alert on low stock.\n"
        "- FR-003: The system shall log every stock adjustment.\n"
    )
    findings = _spec_missing_stakeholder(spec, CATALOG)
    assert findings == []


def test_personas_heading_silences() -> None:
    """Spec with ## Personas heading → silent."""
    spec = _make_spec(
        "# Mobile App Spec\n\n"
        "## Personas\n\n"
        "- Alice: frequent traveller booking flights.\n"
        "- Bob: occasional user checking itinerary.\n\n"
        "## Requirements\n\n"
        "- FR-001: The app shall support offline itinerary access.\n"
        "- FR-002: The app shall send push notifications on flight change.\n"
        "- FR-003: The app shall allow seat selection.\n"
    )
    findings = _spec_missing_stakeholder(spec, CATALOG)
    assert findings == []


def test_actors_heading_silences() -> None:
    """Spec with ## Actors heading → silent."""
    spec = _make_spec(
        "# Notification Spec\n\n"
        "## Actors\n\n"
        "- Subscriber: receives notifications.\n"
        "- Publisher: sends events.\n\n"
        "## Requirements\n\n"
        "- FR-001: The system shall deliver notifications within 5 seconds.\n"
        "- FR-002: The system shall support email and SMS channels.\n"
        "- FR-003: The system shall allow subscribers to opt out.\n"
    )
    findings = _spec_missing_stakeholder(spec, CATALOG)
    assert findings == []


def test_user_types_heading_silences() -> None:
    """Spec with ## User Types heading → silent."""
    spec = _make_spec(
        "# CMS Spec\n\n"
        "## User Types\n\n"
        "- Editor: creates and publishes content.\n"
        "- Reviewer: approves drafts.\n\n"
        "## Requirements\n\n"
        "- FR-001: The system shall support draft/publish workflow.\n"
        "- FR-002: The system shall record revision history.\n"
        "- FR-003: The system shall allow scheduling future publication.\n"
    )
    findings = _spec_missing_stakeholder(spec, CATALOG)
    assert findings == []


def test_fewer_than_three_fr_lines_silent() -> None:
    """Spec with only 2 FR- lines → silent (guard not met)."""
    spec = _make_spec(
        "# Minimal Spec\n\n"
        "## Requirements\n\n"
        "- FR-001: The system shall do X.\n"
        "- FR-002: The system shall do Y.\n"
    )
    findings = _spec_missing_stakeholder(spec, CATALOG)
    assert findings == []


def test_plan_artifact_is_silent() -> None:
    """Plan artifact → always silent."""
    plan = _make_plan(
        "# Deployment Plan\n\n"
        "## Deploy Steps\n\n"
        "- FR-001: something\n"
        "- FR-002: something\n"
        "- FR-003: something\n"
    )
    findings = _spec_missing_stakeholder(plan, CATALOG)
    assert findings == []


def test_tasks_artifact_is_silent() -> None:
    """Tasks artifact → always silent."""
    tasks = _make_tasks(
        "# Tasks\n\n"
        "- [ ] T001 [US1] FR-001: implement login.\n"
        "- [ ] T002 [US1] FR-002: implement logout.\n"
        "- [ ] T003 [US2] FR-003: implement profile page.\n"
    )
    findings = _spec_missing_stakeholder(tasks, CATALOG)
    assert findings == []


def test_fenced_fr_lines_not_counted_toward_guard() -> None:
    """FR- lines inside a fenced code block must not count toward the guard."""
    spec = _make_spec(
        "# Example Spec\n\n"
        "## Overview\n\nSome prose.\n\n"
        "```\n"
        "FR-001: ignore me\n"
        "FR-002: ignore me too\n"
        "FR-003: still inside fence\n"
        "```\n"
        "\n## Requirements\n\n"
        "Only 2 real FR lines here:\n"
        "- FR-004: The system shall do A.\n"
        "- FR-005: The system shall do B.\n"
    )
    findings = _spec_missing_stakeholder(spec, CATALOG)
    # Guard requires ≥3 non-fenced FR/NFR lines; only 2 real ones → silent.
    assert findings == []


def test_affected_parties_heading_silences() -> None:
    """Spec with ## Affected Parties heading → silent."""
    spec = _make_spec(
        "# Data Pipeline Spec\n\n"
        "## Affected Parties\n\n"
        "- Data Engineering: maintains the pipeline.\n"
        "- Analytics: consumes output datasets.\n\n"
        "## Requirements\n\n"
        "- FR-001: The pipeline shall process events within 30 seconds.\n"
        "- FR-002: The pipeline shall output to BigQuery.\n"
        "- FR-003: The pipeline shall support replay from checkpoints.\n"
    )
    findings = _spec_missing_stakeholder(spec, CATALOG)
    assert findings == []
