"""Tests for SPEC-MAQA-MISSING-PRIORITY pitfall.

Fires when a spec has ≥3 non-fenced FR-NNN requirement lines but no priority
annotation anywhere in the document (MoSCoW labels, P1/P2/P3 designators,
or High/Medium/Low Priority markers).

Sources:
  - MAQA 'Modifiability' attribute (requirements must carry relative priority)
  - INVEST 'Negotiable' principle
  - QVscribe Level-2 'Prioritization' quality attribute
"""

from __future__ import annotations

import pytest

from sddgrade.adapters.base import parse_sections
from sddgrade.catalog import load_catalog
from sddgrade.engine.lint import _spec_maqa_missing_priority
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


def test_three_fr_lines_no_priority_fires() -> None:
    """Spec with exactly 3 FR- lines and no priority marker → fires."""
    spec = _make_spec(
        "# Feature Spec\n\n"
        "## Requirements\n\n"
        "- FR-001: The system shall export tasks as CSV.\n"
        "- FR-002: The system shall filter exports by status.\n"
        "- FR-003: The system shall escape CSV field values per RFC 4180.\n"
    )
    findings = _spec_maqa_missing_priority(spec, CATALOG)
    assert len(findings) == 1
    assert findings[0].pitfall_id == "SPEC-MAQA-MISSING-PRIORITY"
    assert "priority" in findings[0].message.lower()


def test_five_fr_lines_no_priority_fires() -> None:
    """Spec with 5 FR- lines and no priority marker → fires once."""
    spec = _make_spec(
        "# Feature Spec\n\n"
        "## Overview\n\nThis feature enables bulk task operations.\n\n"
        "## Requirements\n\n"
        "- FR-001: The system shall list all tasks.\n"
        "- FR-002: The system shall mark tasks complete.\n"
        "- FR-003: The system shall delete tasks.\n"
        "- FR-004: The system shall archive tasks.\n"
        "- FR-005: The system shall restore archived tasks.\n"
    )
    findings = _spec_maqa_missing_priority(spec, CATALOG)
    assert len(findings) == 1
    assert findings[0].pitfall_id == "SPEC-MAQA-MISSING-PRIORITY"


def test_finding_anchored_to_line_1() -> None:
    """Aggregate finding is anchored to line 1."""
    spec = _make_spec(
        "# Spec\n\n"
        "## Requirements\n\n"
        "- FR-001: The system shall do A.\n"
        "- FR-002: The system shall do B.\n"
        "- FR-003: The system shall do C.\n"
    )
    findings = _spec_maqa_missing_priority(spec, CATALOG)
    assert len(findings) == 1
    assert findings[0].line == 1


def test_fr_lines_scattered_across_sections_fires() -> None:
    """FR lines spread across multiple sections still trigger the guard."""
    spec = _make_spec(
        "# Spec\n\n"
        "## Authentication\n\n"
        "- FR-001: The system shall authenticate users.\n\n"
        "## Export\n\n"
        "- FR-002: The system shall export data.\n\n"
        "## Storage\n\n"
        "- FR-003: The system shall persist records.\n"
    )
    findings = _spec_maqa_missing_priority(spec, CATALOG)
    assert len(findings) == 1


def test_priority_only_in_fenced_block_fires() -> None:
    """Priority marker exclusively inside a fenced code block is ignored → fires."""
    spec = _make_spec(
        "# Spec\n\n"
        "## Requirements\n\n"
        "- FR-001: The system shall do A.\n"
        "- FR-002: The system shall do B.\n"
        "- FR-003: The system shall do C.\n\n"
        "```toml\n"
        "# P1 = high priority items\n"
        "priority = 'high'\n"
        "```\n"
    )
    findings = _spec_maqa_missing_priority(spec, CATALOG)
    assert len(findings) == 1


# ---------------------------------------------------------------------------
# SILENT cases — check must NOT trigger
# ---------------------------------------------------------------------------


def test_p1_p2_priority_labels_silent() -> None:
    """FR requirements with P1/P2 priority designators → silent."""
    spec = _make_spec(
        "# Feature Spec\n\n"
        "### User Story 1 - Export tasks (Priority: P1)\n\n"
        "## Requirements\n\n"
        "- FR-001: The system shall export tasks as CSV.\n"
        "- FR-002: The system shall filter exports by status.\n"
        "- FR-003: The system shall escape CSV field values.\n"
    )
    findings = _spec_maqa_missing_priority(spec, CATALOG)
    assert findings == []


def test_moscow_must_have_silent() -> None:
    """FR requirements with MoSCoW 'must have' annotation → silent."""
    spec = _make_spec(
        "# Feature\n\n"
        "## Requirements\n\n"
        "- FR-001 (Must Have): The system shall export data.\n"
        "- FR-002 (Should Have): The system shall send a notification.\n"
        "- FR-003 (Could Have): The system shall display a progress bar.\n"
    )
    findings = _spec_maqa_missing_priority(spec, CATALOG)
    assert findings == []


def test_moscow_heading_silent() -> None:
    """MoSCoW keyword anywhere in the document → silent."""
    spec = _make_spec(
        "# Feature\n\n"
        "## Priority (MoSCoW)\n\n"
        "All requirements below are Must Have for the initial release.\n\n"
        "## Requirements\n\n"
        "- FR-001: The system shall authenticate users.\n"
        "- FR-002: The system shall log sessions.\n"
        "- FR-003: The system shall invalidate expired tokens.\n"
    )
    findings = _spec_maqa_missing_priority(spec, CATALOG)
    assert findings == []


def test_high_priority_text_silent() -> None:
    """'High Priority' text anywhere in the document → silent."""
    spec = _make_spec(
        "# Feature\n\n"
        "## Requirements\n\n"
        "These are High Priority requirements for the release.\n\n"
        "- FR-001: The system shall process payments.\n"
        "- FR-002: The system shall issue receipts.\n"
        "- FR-003: The system shall record transactions.\n"
    )
    findings = _spec_maqa_missing_priority(spec, CATALOG)
    assert findings == []


def test_priority_equals_high_silent() -> None:
    """'priority: high' text (colon separator) → silent."""
    spec = _make_spec(
        "# Feature\n\n"
        "## Requirements\n\n"
        "- FR-001 priority: high — The system shall serve pages < 200 ms.\n"
        "- FR-002: The system shall cache static assets.\n"
        "- FR-003: The system shall compress responses.\n"
    )
    findings = _spec_maqa_missing_priority(spec, CATALOG)
    assert findings == []


def test_fewer_than_three_fr_lines_silent() -> None:
    """Spec with only 2 FR- lines does not trigger guard → silent."""
    spec = _make_spec(
        "# Feature\n\n"
        "## Requirements\n\n"
        "- FR-001: The system shall export tasks.\n"
        "- FR-002: The system shall send a confirmation email.\n"
    )
    findings = _spec_maqa_missing_priority(spec, CATALOG)
    assert findings == []


def test_no_fr_lines_silent() -> None:
    """Spec with no FR- identifiers at all → silent."""
    spec = _make_spec(
        "# Feature\n\n"
        "## Overview\n\n"
        "The system shall provide task management capabilities.\n"
        "The system shall log all activity.\n"
        "The system shall notify users on changes.\n"
    )
    findings = _spec_maqa_missing_priority(spec, CATALOG)
    assert findings == []


def test_fr_lines_in_fenced_block_not_counted() -> None:
    """FR- identifiers inside fenced code blocks are excluded from the guard count."""
    spec = _make_spec(
        "# Feature\n\n"
        "## Overview\n\n"
        "Only one real requirement below.\n\n"
        "```\n"
        "# FR-001 placeholder\n"
        "# FR-002 placeholder\n"
        "# FR-003 placeholder\n"
        "```\n\n"
        "## Requirements\n\n"
        "- FR-001: The system shall export tasks.\n"
    )
    findings = _spec_maqa_missing_priority(spec, CATALOG)
    # Only 1 real (non-fenced) FR line → guard not met → silent.
    assert findings == []


def test_plan_artifact_not_checked() -> None:
    """Check applies only to spec artifacts (artifacts=['spec'] in catalog)."""
    plan = Artifact(
        path="plan.md",
        type=ArtifactType.PLAN,
        raw=(
            "# Implementation Plan\n\n"
            "## Tasks\n\n"
            "- FR-001: implement auth\n"
            "- FR-002: implement export\n"
            "- FR-003: implement notifications\n"
        ),
        sections=parse_sections(
            "# Implementation Plan\n\n"
            "## Tasks\n\n"
            "- FR-001: implement auth\n"
            "- FR-002: implement export\n"
            "- FR-003: implement notifications\n"
        ),
    )
    findings = _spec_maqa_missing_priority(plan, CATALOG)
    assert findings == []
