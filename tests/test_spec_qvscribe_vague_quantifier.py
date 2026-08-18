"""Tests for SPEC-QVSCRIBE-VAGUE-QUANTIFIER pitfall.

Fires when requirement-bearing lines contain an indefinite quantity word
(several, many, few, some, various, numerous, 'a number of', 'a variety of').
Scoped to requirement-bearing lines via _requirement_mask(); fenced blocks excluded.

Sources:
  - QVscribe Rule QV-112 (Level-1 Clarity defect — indefinite quantifiers)
  - ISO/IEC/IEEE 29148:2018 §5.2.5 verifiable characteristic
"""

from __future__ import annotations

import pytest

from sddgrade.adapters.base import parse_sections
from sddgrade.catalog import load_catalog
from sddgrade.engine.lint import _spec_qvscribe_vague_quantifier
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


def test_several_in_shall_requirement_fires() -> None:
    """'several' on a SHALL requirement line in Requirements section → fires."""
    spec = _make_spec(
        "# Feature Spec\n\n"
        "## Requirements\n\n"
        "- FR-001: The system shall support several concurrent users.\n"
        "- FR-002: The system shall validate the submitted form.\n"
    )
    findings = _spec_qvscribe_vague_quantifier(spec, CATALOG)
    assert len(findings) == 1
    assert findings[0].pitfall_id == "SPEC-QVSCRIBE-VAGUE-QUANTIFIER"
    assert "several" in findings[0].message.lower() or "vague quantifier" in findings[0].message.lower()


def test_many_in_must_requirement_fires() -> None:
    """'many' on a MUST line → fires."""
    spec = _make_spec(
        "# Spec\n\n"
        "## Requirements\n\n"
        "- FR-001: The gateway must handle many simultaneous requests.\n"
    )
    findings = _spec_qvscribe_vague_quantifier(spec, CATALOG)
    assert len(findings) == 1
    assert findings[0].pitfall_id == "SPEC-QVSCRIBE-VAGUE-QUANTIFIER"


def test_various_in_nfr_fires() -> None:
    """'various' on an NFR line → fires."""
    spec = _make_spec(
        "# Spec\n\n"
        "## Requirements\n\n"
        "- NFR-003: The report shall provide various export formats.\n"
    )
    findings = _spec_qvscribe_vague_quantifier(spec, CATALOG)
    assert len(findings) == 1


def test_numerous_fires() -> None:
    """'numerous' on a SHALL line → fires."""
    spec = _make_spec(
        "# Spec\n\n"
        "## Acceptance Criteria\n\n"
        "- AC-001: The system shall support numerous integrations.\n"
    )
    findings = _spec_qvscribe_vague_quantifier(spec, CATALOG)
    assert len(findings) == 1


def test_a_number_of_fires() -> None:
    """'a number of' on a SHALL line → fires."""
    spec = _make_spec(
        "# Spec\n\n"
        "## Requirements\n\n"
        "- FR-002: The dashboard shall display a number of widgets per user.\n"
    )
    findings = _spec_qvscribe_vague_quantifier(spec, CATALOG)
    assert len(findings) == 1


def test_multiple_vague_quantifier_lines_count() -> None:
    """Multiple requirement lines with vague quantifiers → fires once with count > 1."""
    spec = _make_spec(
        "# Feature\n\n"
        "## Requirements\n\n"
        "- FR-001: The system shall support several concurrent users.\n"
        "- FR-002: The API must handle many simultaneous requests.\n"
        "- FR-003: The system shall validate the submitted form.\n"
    )
    findings = _spec_qvscribe_vague_quantifier(spec, CATALOG)
    assert len(findings) == 1
    assert "2" in findings[0].message  # two offending lines


def test_anchors_to_first_offending_line() -> None:
    """Finding anchors to the first offending line number."""
    raw = (
        "# Feature\n\n"
        "## Requirements\n\n"
        "- FR-001: The system shall support several concurrent users.\n"  # line 5
        "- FR-002: The system shall handle many requests.\n"              # line 6
    )
    spec = _make_spec(raw)
    findings = _spec_qvscribe_vague_quantifier(spec, CATALOG)
    assert len(findings) == 1
    assert findings[0].line == 5


# ---------------------------------------------------------------------------
# SILENT cases — check must NOT trigger
# ---------------------------------------------------------------------------


def test_no_vague_quantifier_silent() -> None:
    """Well-formed spec with precise quantities → silent."""
    spec = _make_spec(
        "# Feature Spec\n\n"
        "## Requirements\n\n"
        "- FR-001: The system shall support at least 500 concurrent users.\n"
        "- FR-002: The gateway must handle a minimum of 200 requests per second.\n"
        "- NFR-003: The report shall support PDF, CSV, and XLSX export formats.\n"
    )
    findings = _spec_qvscribe_vague_quantifier(spec, CATALOG)
    assert findings == []


def test_vague_word_in_prose_paragraph_silent() -> None:
    """'several' in a non-requirement prose paragraph (no shall/must/FR-/NFR-) → silent."""
    spec = _make_spec(
        "# Overview\n\n"
        "This feature is used by several teams across the organisation.\n\n"
        "## Requirements\n\n"
        "- FR-001: The system shall provide an export button.\n"
    )
    findings = _spec_qvscribe_vague_quantifier(spec, CATALOG)
    assert findings == []


def test_vague_word_in_fenced_code_block_silent() -> None:
    """Vague quantifier inside a fenced code block → silent."""
    spec = _make_spec(
        "# Spec\n\n"
        "## Requirements\n\n"
        "- FR-001: The system shall process requests.\n\n"
        "```python\n"
        "# supports several concurrent users\n"
        "MAX_USERS = 500\n"
        "```\n"
    )
    findings = _spec_qvscribe_vague_quantifier(spec, CATALOG)
    assert findings == []


def test_few_as_word_in_heading_not_requirement_silent() -> None:
    """'few' in a heading line (not a requirement) → silent."""
    spec = _make_spec(
        "# A Few Notes on the Feature\n\n"
        "## Requirements\n\n"
        "- FR-001: The system shall support at least 100 concurrent users.\n"
    )
    findings = _spec_qvscribe_vague_quantifier(spec, CATALOG)
    assert findings == []


def test_plan_artifact_silent() -> None:
    """Check does not apply to plan artifacts (artifacts=['spec'] in catalog)."""
    plan = Artifact(
        path="plan.md",
        type=ArtifactType.PLAN,
        raw=(
            "# Implementation Plan\n\n"
            "## Deployment\n\n"
            "Deploy the service. Several workers will run.\n"
        ),
        sections=parse_sections(
            "# Implementation Plan\n\n"
            "## Deployment\n\n"
            "Deploy the service. Several workers will run.\n"
        ),
    )
    findings = _spec_qvscribe_vague_quantifier(plan, CATALOG)
    assert findings == []


def test_empty_spec_silent() -> None:
    """Minimal spec with no requirements → silent."""
    spec = _make_spec(
        "# Overview\n\n"
        "This document describes the task export feature.\n"
    )
    findings = _spec_qvscribe_vague_quantifier(spec, CATALOG)
    assert findings == []


def test_some_used_precisely_in_context_silent() -> None:
    """'some' in a non-requirement context (prose paragraph) → silent."""
    spec = _make_spec(
        "# Feature Spec\n\n"
        "## Background\n\n"
        "In some cases users may need to export data to third-party tools.\n\n"
        "## Requirements\n\n"
        "- FR-001: The system shall provide a CSV export option.\n"
    )
    findings = _spec_qvscribe_vague_quantifier(spec, CATALOG)
    assert findings == []
