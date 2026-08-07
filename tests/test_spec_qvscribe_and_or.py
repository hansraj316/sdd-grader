"""Tests for SPEC-QVSCRIBE-AND-OR pitfall.

The check fires when requirement-bearing lines contain the ambiguous conjunction
'and/or'. Fires: ≥1 non-fenced requirement line with \\band/or\\b.
Silent: 'and/or' in prose sections (not scoped to requirements), fenced blocks,
or specs that simply don't use the pattern.

Source: QVscribe Ambiguous Conjunction defect (Level 1 Clarity);
        ISO/IEC/IEEE 29148:2018 §5.2.5(a) 'unambiguous' characteristic.
"""

from __future__ import annotations

import pytest

from sddgrade.adapters.base import parse_sections
from sddgrade.catalog import load_catalog
from sddgrade.engine.lint import _spec_qvscribe_and_or
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


def test_fr_line_with_and_or_in_requirements_fires() -> None:
    """FR-NNN requirement line with 'and/or' in Requirements section → fires."""
    spec = _make_spec(
        "# Feature Spec\n\n"
        "## Requirements\n\n"
        "- FR-001: The system shall accept PDF and/or Word input from the user.\n"
        "- FR-002: The system shall validate the submitted form.\n"
    )
    findings = _spec_qvscribe_and_or(spec, CATALOG)
    assert len(findings) == 1
    assert findings[0].pitfall_id == "SPEC-QVSCRIBE-AND-OR"
    assert "and/or" in findings[0].message.lower()


def test_shall_line_with_and_or_fires() -> None:
    """Normative 'shall' requirement with 'and/or' outside a named Requirements section → fires."""
    spec = _make_spec(
        "# Feature Spec\n\n"
        "## Acceptance Criteria\n\n"
        "The system shall authenticate users and/or issue session tokens on success.\n"
    )
    findings = _spec_qvscribe_and_or(spec, CATALOG)
    assert len(findings) == 1
    assert findings[0].pitfall_id == "SPEC-QVSCRIBE-AND-OR"


def test_multiple_and_or_lines_fires_with_count() -> None:
    """Multiple requirement lines with 'and/or' → fires once with count reflected."""
    spec = _make_spec(
        "# Feature Spec\n\n"
        "## Requirements\n\n"
        "- FR-001: The system shall support CSV and/or JSON export.\n"
        "- FR-002: The user must provide a username and/or email address.\n"
        "- FR-003: The system shall encrypt data at rest.\n"
    )
    findings = _spec_qvscribe_and_or(spec, CATALOG)
    assert len(findings) == 1
    assert "2" in findings[0].message  # 2 occurrences mentioned


def test_and_or_in_acceptance_section_fires() -> None:
    """'and/or' in an Acceptance Criteria section fires."""
    spec = _make_spec(
        "# Spec\n\n"
        "## Acceptance Criteria\n\n"
        "- AC-001: The export must include the user's name and/or email.\n"
    )
    findings = _spec_qvscribe_and_or(spec, CATALOG)
    assert len(findings) == 1


def test_and_or_case_insensitive_fires() -> None:
    """'And/Or' and 'AND/OR' variants are also caught."""
    spec = _make_spec(
        "# Spec\n\n"
        "## Requirements\n\n"
        "- FR-001: The system shall handle PNG And/Or JPEG uploads.\n"
    )
    findings = _spec_qvscribe_and_or(spec, CATALOG)
    assert len(findings) == 1


# ---------------------------------------------------------------------------
# SILENT cases — check must NOT trigger
# ---------------------------------------------------------------------------


def test_no_and_or_in_requirements_silent() -> None:
    """Well-formed spec with no 'and/or' anywhere → silent."""
    spec = _make_spec(
        "# Feature Spec\n\n"
        "## Requirements\n\n"
        "- FR-001: The system shall accept PDF input.\n"
        "- FR-002: The system shall validate the submitted form.\n"
    )
    findings = _spec_qvscribe_and_or(spec, CATALOG)
    assert findings == []


def test_and_or_in_prose_paragraph_silent() -> None:
    """'and/or' in a non-requirement prose paragraph (no shall/must/FR-/NFR-) → silent."""
    spec = _make_spec(
        "# Feature Spec\n\n"
        "## Overview\n\n"
        "This feature allows users to export data. They may choose PDF and/or Word "
        "depending on their preference.\n\n"
        "## Requirements\n\n"
        "- FR-001: The system shall provide an export button.\n"
    )
    findings = _spec_qvscribe_and_or(spec, CATALOG)
    # 'and/or' is in the Overview section, which is not a requirement-bearing section.
    # FR-001 line does not contain 'and/or'.
    assert findings == []


def test_and_or_in_fenced_code_block_silent() -> None:
    """'and/or' inside a fenced code block is excluded → silent."""
    spec = _make_spec(
        "# Spec\n\n"
        "## Requirements\n\n"
        "- FR-001: The system shall process requests.\n\n"
        "```python\n"
        "# accept PDF and/or Word input\n"
        "def process(file_type: str) -> None:\n"
        "    pass\n"
        "```\n"
    )
    findings = _spec_qvscribe_and_or(spec, CATALOG)
    assert findings == []


def test_plain_spec_no_requirements_silent() -> None:
    """Minimal spec with no requirements vocabulary and no 'and/or' → silent."""
    spec = _make_spec(
        "# Overview\n\n"
        "This document describes the task export feature.\n"
    )
    findings = _spec_qvscribe_and_or(spec, CATALOG)
    assert findings == []


def test_non_spec_artifact_type_silent() -> None:
    """Check does not apply to plan artifacts (artifacts=['spec'] in catalog)."""
    plan = Artifact(
        path="plan.md",
        type=ArtifactType.PLAN,
        raw=(
            "# Implementation Plan\n\n"
            "## Deployment\n\n"
            "Deploy the service and/or the worker.\n"
        ),
        sections=parse_sections(
            "# Implementation Plan\n\n"
            "## Deployment\n\n"
            "Deploy the service and/or the worker.\n"
        ),
    )
    findings = _spec_qvscribe_and_or(plan, CATALOG)
    assert findings == []


def test_and_or_anchors_to_first_line() -> None:
    """When multiple 'and/or' lines are found, the finding anchors to the first one."""
    raw = (
        "# Feature\n\n"
        "## Requirements\n\n"
        "- FR-001: The system shall accept CSV and/or JSON output.\n"  # line 5
        "- FR-002: The system shall support Windows and/or Linux.\n"   # line 6
    )
    spec = _make_spec(raw)
    findings = _spec_qvscribe_and_or(spec, CATALOG)
    assert len(findings) == 1
    assert findings[0].line == 5
