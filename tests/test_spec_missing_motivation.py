"""Tests for SPEC-MISSING-MOTIVATION pitfall.

Fires when a spec has ≥3 non-fenced FR-/NFR- requirement lines but no
Problem Statement / Motivation / Background / Rationale / Context / Purpose
section heading.

Sources:
  - Amazon Kiro spec template — mandates a "Problem" section before requirements
  - Tessl spec-first methodology — specs must explain the *why* before the *what*
  - ISO/IEC/IEEE 29148:2018 §5.2.4 — scope/purpose clause is required
  - INVEST Valuable — requirements without stated user value cannot be prioritised
"""

from __future__ import annotations

import pytest

from sddgrade.adapters.base import parse_sections
from sddgrade.catalog import load_catalog
from sddgrade.engine.lint import _spec_missing_motivation
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


def test_three_fr_lines_no_motivation_fires() -> None:
    """Spec with exactly 3 FR- lines and no motivation heading → fires."""
    spec = _make_spec(
        "# Feature Spec\n\n"
        "## Overview\n\nThis feature enables task export.\n\n"
        "## Requirements\n\n"
        "- FR-001: The system shall export tasks as CSV.\n"
        "- FR-002: The system shall filter exports by status.\n"
        "- FR-003: The system shall escape CSV field values per RFC 4180.\n"
    )
    findings = _spec_missing_motivation(spec, CATALOG)
    assert len(findings) == 1
    assert findings[0].pitfall_id == "SPEC-MISSING-MOTIVATION"
    assert "motivation" in findings[0].message.lower()


def test_five_fr_lines_no_motivation_fires_once() -> None:
    """Spec with 5 FR- lines and no motivation heading → fires exactly once."""
    spec = _make_spec(
        "# Feature Spec\n\n"
        "## Overview\n\nBulk task operations.\n\n"
        "## Requirements\n\n"
        "- FR-001: The system shall list all tasks.\n"
        "- FR-002: The system shall mark tasks complete.\n"
        "- FR-003: The system shall delete tasks.\n"
        "- FR-004: The system shall archive tasks.\n"
        "- FR-005: The system shall restore archived tasks.\n"
    )
    findings = _spec_missing_motivation(spec, CATALOG)
    assert len(findings) == 1
    assert findings[0].pitfall_id == "SPEC-MISSING-MOTIVATION"


def test_finding_anchored_to_line_1() -> None:
    """Aggregate finding is anchored to line 1."""
    spec = _make_spec(
        "# Spec\n\n"
        "## Requirements\n\n"
        "- FR-001: The system shall do A.\n"
        "- FR-002: The system shall do B.\n"
        "- FR-003: The system shall do C.\n"
    )
    findings = _spec_missing_motivation(spec, CATALOG)
    assert len(findings) == 1
    assert findings[0].line == 1


def test_nfr_lines_trigger_guard() -> None:
    """NFR- lines count toward the ≥3 guard threshold."""
    spec = _make_spec(
        "# Spec\n\n"
        "## Requirements\n\n"
        "- NFR-001: The system shall respond in < 200 ms.\n"
        "- NFR-002: The system shall achieve 99.9% uptime.\n"
        "- NFR-003: The system shall encrypt data at rest with AES-256.\n"
    )
    findings = _spec_missing_motivation(spec, CATALOG)
    assert len(findings) == 1
    assert findings[0].pitfall_id == "SPEC-MISSING-MOTIVATION"


def test_mixed_fr_nfr_lines_trigger_guard() -> None:
    """A mix of FR- and NFR- lines triggers the guard when total ≥ 3."""
    spec = _make_spec(
        "# Spec\n\n"
        "## Requirements\n\n"
        "- FR-001: The system shall export data.\n"
        "- NFR-001: The system shall respond in < 300 ms.\n"
        "- FR-002: The system shall filter by date range.\n"
    )
    findings = _spec_missing_motivation(spec, CATALOG)
    assert len(findings) == 1
    assert findings[0].pitfall_id == "SPEC-MISSING-MOTIVATION"


def test_spec_with_success_criteria_but_no_motivation_fires() -> None:
    """Spec with Success Criteria and Glossary but no motivation → fires."""
    spec = _make_spec(
        "# Feature Spec\n\n"
        "## Requirements\n\n"
        "- FR-001: The system shall index documents.\n"
        "- FR-002: The system shall support full-text search.\n"
        "- FR-003: The system shall rank results by relevance.\n\n"
        "## Success Criteria\n\n"
        "- Search returns results in < 1 s for 99% of queries.\n\n"
        "## Glossary\n\n"
        "- Index: a searchable data structure.\n"
    )
    findings = _spec_missing_motivation(spec, CATALOG)
    assert len(findings) == 1
    assert findings[0].pitfall_id == "SPEC-MISSING-MOTIVATION"


# ---------------------------------------------------------------------------
# PASS cases — check should be silent
# ---------------------------------------------------------------------------


def test_problem_statement_heading_silences_check() -> None:
    """Spec with `## Problem Statement` heading → silent."""
    spec = _make_spec(
        "# Feature Spec\n\n"
        "## Problem Statement\n\n"
        "Users need to export tasks to share with stakeholders.\n\n"
        "## Requirements\n\n"
        "- FR-001: The system shall export tasks as CSV.\n"
        "- FR-002: The system shall filter exports by status.\n"
        "- FR-003: The system shall escape CSV field values.\n"
    )
    findings = _spec_missing_motivation(spec, CATALOG)
    assert findings == []


def test_motivation_heading_silences_check() -> None:
    """Spec with `## Motivation` heading → silent."""
    spec = _make_spec(
        "# Feature Spec\n\n"
        "## Motivation\n\n"
        "Manual copy-paste of tasks is error-prone and slow.\n\n"
        "## Requirements\n\n"
        "- FR-001: The system shall authenticate users.\n"
        "- FR-002: The system shall issue JWT tokens.\n"
        "- FR-003: The system shall revoke sessions.\n"
    )
    findings = _spec_missing_motivation(spec, CATALOG)
    assert findings == []


def test_background_heading_silences_check() -> None:
    """Spec with `## Background` heading → silent."""
    spec = _make_spec(
        "# Feature Spec\n\n"
        "## Background\n\n"
        "The current system lacks a bulk-import capability.\n\n"
        "## Requirements\n\n"
        "- FR-001: The system shall export data.\n"
        "- FR-002: The system shall import data.\n"
        "- FR-003: The system shall validate data integrity.\n"
    )
    findings = _spec_missing_motivation(spec, CATALOG)
    assert findings == []


def test_rationale_heading_silences_check() -> None:
    """Spec with `## Rationale` heading → silent."""
    spec = _make_spec(
        "# Feature Spec\n\n"
        "## Rationale\n\n"
        "Replacing manual entry reduces error rates by 40%.\n\n"
        "## Requirements\n\n"
        "- FR-001: The system shall send email notifications.\n"
        "- FR-002: The system shall queue notifications.\n"
        "- NFR-001: The system shall deliver within 30 s.\n"
    )
    findings = _spec_missing_motivation(spec, CATALOG)
    assert findings == []


def test_context_heading_silences_check() -> None:
    """Spec with `## Context` heading → silent."""
    spec = _make_spec(
        "# Feature Spec\n\n"
        "## Context\n\n"
        "Stakeholders need weekly CSV exports for board reporting.\n\n"
        "## Requirements\n\n"
        "- FR-001: The system shall do A.\n"
        "- FR-002: The system shall do B.\n"
        "- FR-003: The system shall do C.\n"
    )
    findings = _spec_missing_motivation(spec, CATALOG)
    assert findings == []


def test_purpose_heading_silences_check() -> None:
    """Spec with `## Purpose` heading → silent."""
    spec = _make_spec(
        "# Feature Spec\n\n"
        "## Purpose\n\n"
        "Enable programmatic access to task data.\n\n"
        "## Requirements\n\n"
        "- FR-001: The system shall export tasks.\n"
        "- FR-002: The system shall filter by status.\n"
        "- FR-003: The system shall validate the schema.\n"
    )
    findings = _spec_missing_motivation(spec, CATALOG)
    assert findings == []


def test_fewer_than_three_req_lines_is_silent() -> None:
    """Spec with fewer than 3 FR-/NFR- lines does not fire."""
    spec = _make_spec(
        "# Minimal Spec\n\n"
        "## Overview\n\nSmall feature.\n\n"
        "## Requirements\n\n"
        "- FR-001: The system shall do A.\n"
        "- FR-002: The system shall do B.\n"
    )
    findings = _spec_missing_motivation(spec, CATALOG)
    assert findings == []


def test_no_fr_lines_at_all_is_silent() -> None:
    """Spec with no formal FR-/NFR- identifiers → guard does not trip → silent."""
    spec = _make_spec(
        "# Spec\n\n"
        "## Overview\n\nDescribes something.\n\n"
        "## Requirements\n\n"
        "The system shall authenticate users.\n"
        "The system shall log errors.\n"
    )
    findings = _spec_missing_motivation(spec, CATALOG)
    assert findings == []


def test_fr_lines_inside_code_fence_not_counted() -> None:
    """FR- identifiers inside a code fence do not count toward the guard."""
    spec = _make_spec(
        "# Spec\n\n"
        "## Overview\n\n"
        "```\n"
        "- FR-001: example\n"
        "- FR-002: example\n"
        "- FR-003: example\n"
        "- FR-004: example\n"
        "```\n"
        "\n"
        "## Requirements\n\n"
        "Only two real requirements:\n"
        "- FR-001: The system shall do A.\n"
        "- FR-002: The system shall do B.\n"
    )
    # Only 2 non-fenced FR- lines → guard should NOT fire.
    findings = _spec_missing_motivation(spec, CATALOG)
    assert findings == []


def test_non_spec_artifact_type_is_silent() -> None:
    """The check only applies to SPEC artifacts; plan artifacts are silenced."""
    art = Artifact(
        path="plan.md",
        type=ArtifactType.PLAN,
        raw=(
            "## Plan\n\n"
            "- FR-001: The system shall do A.\n"
            "- FR-002: The system shall do B.\n"
            "- FR-003: The system shall do C.\n"
        ),
        sections=parse_sections(
            "## Plan\n\n"
            "- FR-001: The system shall do A.\n"
            "- FR-002: The system shall do B.\n"
            "- FR-003: The system shall do C.\n"
        ),
    )
    findings = _spec_missing_motivation(art, CATALOG)
    assert findings == []
