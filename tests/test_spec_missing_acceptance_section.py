"""Tests for SPEC-MISSING-ACCEPTANCE-SECTION lint check.

Fires when a spec has ≥3 FR-/NFR- requirement lines but no section heading
matching Acceptance Criteria / Acceptance Tests / Verification / Testing Criteria /
Definition of Done / Fit Criteria / Test Cases / Test Plan
(Canon Volere fit criteria, MAQA binary verifiability, ISO/IEC/IEEE 29148:2018 §5.2.4(b)).
"""
from __future__ import annotations

import pytest

from sddgrade.adapters.base import parse_sections
from sddgrade.catalog import load_catalog
from sddgrade.engine.lint import _spec_missing_acceptance_section
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
# FIRE cases — should detect SPEC-MISSING-ACCEPTANCE-SECTION
# ---------------------------------------------------------------------------

def test_three_fr_lines_no_acceptance_section_fires() -> None:
    """Spec with exactly 3 FR- lines and no acceptance section heading → fires."""
    spec = _make_spec(
        "# Widget Service Spec\n\n"
        "## Problem Statement\n\nWe need a widget service.\n\n"
        "## Stakeholders\n\n- End User: uses widgets.\n\n"
        "## Requirements\n\n"
        "- FR-001: The system shall process widgets within 200 ms.\n"
        "- FR-002: The system shall store up to 10 000 widgets.\n"
        "- FR-003: The system shall support concurrent access by 50 users.\n"
    )
    findings = _spec_missing_acceptance_section(spec, CATALOG)
    assert len(findings) == 1
    assert findings[0].pitfall_id == "SPEC-MISSING-ACCEPTANCE-SECTION"
    assert "acceptance" in findings[0].message.lower()


def test_five_fr_lines_no_acceptance_section_fires_exactly_once() -> None:
    """Spec with 5 FR- lines and no acceptance section → fires exactly once."""
    spec = _make_spec(
        "# Reporting Spec\n\n"
        "## Motivation\n\nEnable reporting.\n\n"
        "## Stakeholders\n\n- Analyst: reviews reports.\n\n"
        "## Requirements\n\n"
        "- FR-001: The system shall generate PDF reports.\n"
        "- FR-002: The system shall schedule weekly exports.\n"
        "- FR-003: The system shall email reports to subscribers.\n"
        "- FR-004: The system shall support filtering by date range.\n"
        "- FR-005: The system shall archive reports older than 90 days.\n"
    )
    findings = _spec_missing_acceptance_section(spec, CATALOG)
    assert len(findings) == 1, "Should fire exactly once regardless of FR count"
    assert findings[0].pitfall_id == "SPEC-MISSING-ACCEPTANCE-SECTION"
    assert findings[0].line == 1


def test_mixed_fr_nfr_no_acceptance_section_fires() -> None:
    """Spec with FR- and NFR- lines but no acceptance section heading → fires."""
    spec = _make_spec(
        "# Payment API Spec\n\n"
        "## Motivation\n\nEnable payment processing.\n\n"
        "## Glossary\n\n- Widget: a billable unit.\n\n"
        "## Requirements\n\n"
        "- FR-001: The system shall process payments.\n"
        "- FR-002: The system shall validate card numbers per PCI-DSS.\n"
        "- NFR-001: The API shall respond within 500 ms at the 95th percentile.\n"
    )
    findings = _spec_missing_acceptance_section(spec, CATALOG)
    assert len(findings) == 1
    assert findings[0].pitfall_id == "SPEC-MISSING-ACCEPTANCE-SECTION"


def test_inline_bold_ac_does_not_silence() -> None:
    """Bold **Acceptance criteria** text (not a heading) does not silence the check."""
    spec = _make_spec(
        "# Notification Spec\n\n"
        "## Requirements\n\n"
        "- FR-001: The system shall send emails.\n"
        "- FR-002: The system shall send SMS alerts.\n"
        "- FR-003: The system shall support opt-out.\n\n"
        "**Acceptance criteria**\n\n"
        "- Users receive emails within 5 seconds.\n"
    )
    findings = _spec_missing_acceptance_section(spec, CATALOG)
    # Bold text is prose, not a section heading; check should still fire.
    assert len(findings) == 1
    assert findings[0].pitfall_id == "SPEC-MISSING-ACCEPTANCE-SECTION"


# ---------------------------------------------------------------------------
# SILENT cases — must NOT fire SPEC-MISSING-ACCEPTANCE-SECTION
# ---------------------------------------------------------------------------

def test_acceptance_criteria_heading_silences() -> None:
    """Spec with ## Acceptance Criteria heading → silent."""
    spec = _make_spec(
        "# Auth Service Spec\n\n"
        "## Requirements\n\n"
        "- FR-001: The system shall support OAuth 2.0 login.\n"
        "- FR-002: The system shall lock accounts after 5 failed attempts.\n"
        "- FR-003: The system shall email password-reset links.\n\n"
        "## Acceptance Criteria\n\n"
        "- Given a valid OAuth token, when login is attempted, then access is granted.\n"
    )
    findings = _spec_missing_acceptance_section(spec, CATALOG)
    assert findings == []


def test_verification_heading_silences() -> None:
    """Spec with ## Verification heading → silent."""
    spec = _make_spec(
        "# Inventory Spec\n\n"
        "## Requirements\n\n"
        "- FR-001: The system shall display current stock levels.\n"
        "- FR-002: The system shall alert on low stock.\n"
        "- FR-003: The system shall log every stock adjustment.\n\n"
        "## Verification\n\n"
        "- Stock levels are accurate within 1 minute of update.\n"
    )
    findings = _spec_missing_acceptance_section(spec, CATALOG)
    assert findings == []


def test_definition_of_done_heading_silences() -> None:
    """Spec with ## Definition of Done heading → silent."""
    spec = _make_spec(
        "# Mobile App Spec\n\n"
        "## Requirements\n\n"
        "- FR-001: The app shall support offline itinerary access.\n"
        "- FR-002: The app shall send push notifications on flight change.\n"
        "- FR-003: The app shall allow seat selection.\n\n"
        "## Definition of Done\n\n"
        "- All unit tests pass with ≥90% coverage.\n"
        "- Feature is code-reviewed and merged.\n"
    )
    findings = _spec_missing_acceptance_section(spec, CATALOG)
    assert findings == []


def test_fit_criteria_heading_silences() -> None:
    """Spec with ## Fit Criteria heading → silent."""
    spec = _make_spec(
        "# Data Pipeline Spec\n\n"
        "## Requirements\n\n"
        "- FR-001: The pipeline shall process events within 30 seconds.\n"
        "- FR-002: The pipeline shall output to BigQuery.\n"
        "- FR-003: The pipeline shall support replay from checkpoints.\n\n"
        "## Fit Criteria\n\n"
        "- Pipeline processes 10 000 events per minute without backlog.\n"
    )
    findings = _spec_missing_acceptance_section(spec, CATALOG)
    assert findings == []


def test_test_cases_heading_silences() -> None:
    """Spec with ## Test Cases heading → silent."""
    spec = _make_spec(
        "# CMS Spec\n\n"
        "## Requirements\n\n"
        "- FR-001: The system shall support draft/publish workflow.\n"
        "- FR-002: The system shall record revision history.\n"
        "- FR-003: The system shall allow scheduling future publication.\n\n"
        "## Test Cases\n\n"
        "- TC-001: publish a draft and verify it appears publicly.\n"
    )
    findings = _spec_missing_acceptance_section(spec, CATALOG)
    assert findings == []


def test_acceptance_tests_heading_silences() -> None:
    """Spec with ## Acceptance Tests heading → silent."""
    spec = _make_spec(
        "# Export Spec\n\n"
        "## Requirements\n\n"
        "- FR-001: The system shall export to CSV.\n"
        "- FR-002: The system shall escape field values per RFC 4180.\n"
        "- FR-003: The system shall complete export within 2 seconds.\n\n"
        "## Acceptance Tests\n\n"
        "- AT-001: exported file opens in Excel without errors.\n"
    )
    findings = _spec_missing_acceptance_section(spec, CATALOG)
    assert findings == []


def test_test_plan_heading_silences() -> None:
    """Spec with ## Test Plan heading → silent."""
    spec = _make_spec(
        "# Search Spec\n\n"
        "## Requirements\n\n"
        "- FR-001: The system shall return results within 500 ms.\n"
        "- FR-002: The system shall rank results by relevance.\n"
        "- FR-003: The system shall support fuzzy matching.\n\n"
        "## Test Plan\n\n"
        "- Unit tests: tokenizer, ranker.\n"
        "- Integration tests: end-to-end search flow.\n"
    )
    findings = _spec_missing_acceptance_section(spec, CATALOG)
    assert findings == []


def test_fewer_than_three_fr_lines_silent() -> None:
    """Spec with only 2 FR- lines → silent (guard not met)."""
    spec = _make_spec(
        "# Minimal Spec\n\n"
        "## Requirements\n\n"
        "- FR-001: The system shall do X.\n"
        "- FR-002: The system shall do Y.\n"
    )
    findings = _spec_missing_acceptance_section(spec, CATALOG)
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
    findings = _spec_missing_acceptance_section(plan, CATALOG)
    assert findings == []


def test_tasks_artifact_is_silent() -> None:
    """Tasks artifact → always silent."""
    tasks = _make_tasks(
        "# Tasks\n\n"
        "- [ ] T001 [US1] FR-001: implement login.\n"
        "- [ ] T002 [US1] FR-002: implement logout.\n"
        "- [ ] T003 [US2] FR-003: implement profile page.\n"
    )
    findings = _spec_missing_acceptance_section(tasks, CATALOG)
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
    findings = _spec_missing_acceptance_section(spec, CATALOG)
    # Guard requires ≥3 non-fenced FR/NFR lines; only 2 real ones → silent.
    assert findings == []
