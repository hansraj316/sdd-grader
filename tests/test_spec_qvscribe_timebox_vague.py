"""Tests for SPEC-QVSCRIBE-TIMEBOX-VAGUE pitfall.

Fires when normative requirement lines (shall/must or FR-/NFR- identifier) use a
qualitative timing phrase with no numeric bound:
  - 'as soon as possible' / 'ASAP'
  - 'promptly'
  - 'in a timely manner'
  - 'without delay' / 'without undue delay'
  - 'at the earliest opportunity' / 'at the earliest convenience'

Silent when the same line also contains a numeric time unit (ms, s, sec, min,
hour, day, or 'per second'/'per minute').

Sources:
  - QVscribe Imprecise Timebox defect class
  - ISO/IEC/IEEE 29148:2018 §5.2.5(i): requirement must be verifiable by finite means
"""

from __future__ import annotations

import pytest

from sddgrade.adapters.base import parse_sections
from sddgrade.catalog import load_catalog
from sddgrade.engine.lint import _spec_qvscribe_timebox_vague
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


def test_fires_as_soon_as_possible() -> None:
    """'as soon as possible' on a SHALL requirement line → fires."""
    spec = _make_spec(
        "# Spec\n\n"
        "## Requirements\n\n"
        "- FR-001: The system shall notify the user as soon as possible.\n"
    )
    findings = _spec_qvscribe_timebox_vague(spec, CATALOG)
    assert len(findings) == 1
    assert findings[0].pitfall_id == "SPEC-QVSCRIBE-TIMEBOX-VAGUE"
    assert "timely" in findings[0].message.lower() or "vague" in findings[0].message.lower()


def test_fires_asap() -> None:
    """'ASAP' on a SHALL requirement line → fires."""
    spec = _make_spec(
        "# Spec\n\n"
        "## Functional Requirements\n\n"
        "- FR-002: The system shall respond ASAP to all user requests.\n"
    )
    findings = _spec_qvscribe_timebox_vague(spec, CATALOG)
    assert len(findings) == 1
    assert findings[0].pitfall_id == "SPEC-QVSCRIBE-TIMEBOX-VAGUE"


def test_fires_promptly() -> None:
    """'promptly' on a MUST requirement line → fires."""
    spec = _make_spec(
        "# Spec\n\n"
        "## Functional Requirements\n\n"
        "- FR-003: The system must process all incoming events promptly.\n"
    )
    findings = _spec_qvscribe_timebox_vague(spec, CATALOG)
    assert len(findings) == 1
    assert findings[0].pitfall_id == "SPEC-QVSCRIBE-TIMEBOX-VAGUE"


def test_fires_in_a_timely_manner() -> None:
    """'in a timely manner' on a SHALL requirement line → fires."""
    spec = _make_spec(
        "# Spec\n\n"
        "## Requirements\n\n"
        "- FR-004: Alerts shall be delivered in a timely manner.\n"
    )
    findings = _spec_qvscribe_timebox_vague(spec, CATALOG)
    assert len(findings) == 1
    assert findings[0].pitfall_id == "SPEC-QVSCRIBE-TIMEBOX-VAGUE"


def test_fires_without_delay() -> None:
    """'without delay' on a SHALL requirement line → fires."""
    spec = _make_spec(
        "# Spec\n\n"
        "## Functional Requirements\n\n"
        "- FR-005: The system shall forward requests without delay.\n"
    )
    findings = _spec_qvscribe_timebox_vague(spec, CATALOG)
    assert len(findings) == 1
    assert findings[0].pitfall_id == "SPEC-QVSCRIBE-TIMEBOX-VAGUE"


def test_fires_without_undue_delay() -> None:
    """'without undue delay' on a MUST requirement line → fires."""
    spec = _make_spec(
        "# Spec\n\n"
        "## Non-Functional Requirements\n\n"
        "- FR-006: The gateway must acknowledge messages without undue delay.\n"
    )
    findings = _spec_qvscribe_timebox_vague(spec, CATALOG)
    assert len(findings) == 1
    assert findings[0].pitfall_id == "SPEC-QVSCRIBE-TIMEBOX-VAGUE"


def test_fires_at_the_earliest_opportunity() -> None:
    """'at the earliest opportunity' on a SHALL requirement line → fires."""
    spec = _make_spec(
        "# Spec\n\n"
        "## Requirements\n\n"
        "- FR-007: Pending jobs shall be retried at the earliest opportunity.\n"
    )
    findings = _spec_qvscribe_timebox_vague(spec, CATALOG)
    assert len(findings) == 1
    assert findings[0].pitfall_id == "SPEC-QVSCRIBE-TIMEBOX-VAGUE"


def test_fires_multiple_lines_one_finding() -> None:
    """Multiple offending lines → single aggregate finding with count."""
    spec = _make_spec(
        "# Spec\n\n"
        "## Requirements\n\n"
        "- FR-008: The system shall sync data promptly.\n"
        "- FR-009: The system shall send confirmations without delay.\n"
        "- FR-010: Reports shall be generated as soon as possible.\n"
    )
    findings = _spec_qvscribe_timebox_vague(spec, CATALOG)
    assert len(findings) == 1
    assert "3" in findings[0].message


# ---------------------------------------------------------------------------
# SILENT cases — check should NOT trigger
# ---------------------------------------------------------------------------


def test_silent_with_numeric_ms() -> None:
    """Vague phrase + '200ms' numeric bound → silent (already verifiable)."""
    spec = _make_spec(
        "# Spec\n\n"
        "## Requirements\n\n"
        "- FR-011: The system shall respond within 200ms without delay if network is available.\n"
    )
    findings = _spec_qvscribe_timebox_vague(spec, CATALOG)
    assert findings == [], "Should be silent when numeric time unit (200ms) is present"


def test_silent_with_numeric_seconds() -> None:
    """Vague phrase + '5 seconds' → silent."""
    spec = _make_spec(
        "# Spec\n\n"
        "## Requirements\n\n"
        "- FR-012: The system shall notify users within 5 seconds, as soon as possible.\n"
    )
    findings = _spec_qvscribe_timebox_vague(spec, CATALOG)
    assert findings == [], "Should be silent when numeric seconds bound is present"


def test_silent_prose_no_modal() -> None:
    """Vague phrase in prose with no modal or req-id signal → silent."""
    spec = _make_spec(
        "# Overview\n\n"
        "The team aims to respond as soon as possible to user needs.\n\n"
        "# Background\n\n"
        "Designed for low-latency operation.\n"
    )
    findings = _spec_qvscribe_timebox_vague(spec, CATALOG)
    assert findings == [], "Should be silent when phrase is in prose with no requirement-bearing signal"


def test_silent_fenced_code_block() -> None:
    """Vague phrase inside a fenced code block → silent."""
    spec = _make_spec(
        "# Spec\n\n"
        "## Requirements\n\n"
        "```\n"
        "# FR-013: The system shall respond promptly.\n"
        "```\n"
    )
    findings = _spec_qvscribe_timebox_vague(spec, CATALOG)
    assert findings == [], "Should be silent inside fenced code block"


def test_silent_well_formed_latency_requirement() -> None:
    """Properly bounded requirement → silent."""
    spec = _make_spec(
        "# Spec\n\n"
        "## Requirements\n\n"
        "- FR-014: The system shall process all requests within 500 ms under normal load.\n"
    )
    findings = _spec_qvscribe_timebox_vague(spec, CATALOG)
    assert findings == [], "Well-formed requirement with numeric bound should be silent"


def test_silent_per_second_numeric_unit() -> None:
    """'per second' with a number counts as a time unit — silences the check."""
    spec = _make_spec(
        "# Spec\n\n"
        "## Requirements\n\n"
        "- NFR-015: The system shall handle 1000 requests per second without delay during peak load.\n"
    )
    findings = _spec_qvscribe_timebox_vague(spec, CATALOG)
    assert findings == [], "Should be silent when 'per second' numeric unit is present"


def test_silent_plan_artifact() -> None:
    """Check does not apply to plan artifacts."""
    art = Artifact(
        path="plan.md",
        type=ArtifactType.PLAN,
        raw=(
            "# Plan\n\n"
            "## Deployment\n\n"
            "- The deployment shall complete promptly after approval.\n"
        ),
        sections=parse_sections(
            "# Plan\n\n"
            "## Deployment\n\n"
            "- The deployment shall complete promptly after approval.\n"
        ),
    )
    findings = _spec_qvscribe_timebox_vague(art, CATALOG)
    assert findings == [], "SPEC-QVSCRIBE-TIMEBOX-VAGUE should not apply to plan artifacts"
