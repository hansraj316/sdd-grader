"""Tests for SPEC-QVSCRIBE-INDIRECT-REFERENCE pitfall.

The check fires when normative requirement lines (shall/must/FR-/NFR-) contain a
positional intra-document cross-reference ('as mentioned above', 'see section',
'per section', etc.) that makes the requirement non-self-contained.

Fires: ≥1 non-fenced, non-blockquote requirement line with such a phrase, and the
phrase is NOT inside parentheses.
Silent: phrase in prose section (not a requirement), fenced block, blockquote,
inside parentheses, or no indirect reference at all.

Source: QVscribe Indirect Reference defect (Level 2 Clarity);
        ISO/IEC/IEEE 29148:2018 §5.2.1.2 (individually verifiable / self-contained).
"""

from __future__ import annotations

import pytest

from sddgrade.adapters.base import parse_sections
from sddgrade.catalog import load_catalog
from sddgrade.engine.lint import _spec_qvscribe_indirect_reference
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


def test_as_mentioned_above_in_fr_line_fires() -> None:
    """FR-NNN line with 'as mentioned above' in Requirements section → fires."""
    spec = _make_spec(
        "# Feature Spec\n\n"
        "## Requirements\n\n"
        "- FR-001: The system shall enforce the rate limits as mentioned above.\n"
        "- FR-002: The system shall log all access events.\n"
    )
    findings = _spec_qvscribe_indirect_reference(spec, CATALOG)
    assert len(findings) == 1
    assert findings[0].pitfall_id == "SPEC-QVSCRIBE-INDIRECT-REFERENCE"
    assert "above" in findings[0].message.lower()


def test_see_section_in_shall_line_fires() -> None:
    """'see section' on a normative shall line → fires."""
    spec = _make_spec(
        "# Auth Spec\n\n"
        "## Requirements\n\n"
        "The system shall store tokens using the method described — see section 3.2 for details.\n"
    )
    findings = _spec_qvscribe_indirect_reference(spec, CATALOG)
    assert len(findings) == 1
    assert findings[0].pitfall_id == "SPEC-QVSCRIBE-INDIRECT-REFERENCE"


def test_per_section_in_must_line_fires() -> None:
    """'per section' on a normative must line → fires."""
    spec = _make_spec(
        "# Payment Spec\n\n"
        "## Acceptance Criteria\n\n"
        "- AC-001: The system must process refunds per section 5 of this document.\n"
    )
    findings = _spec_qvscribe_indirect_reference(spec, CATALOG)
    assert len(findings) == 1
    assert findings[0].pitfall_id == "SPEC-QVSCRIBE-INDIRECT-REFERENCE"


def test_as_described_above_in_nfr_line_fires() -> None:
    """'as described above' on an NFR requirement line → fires."""
    spec = _make_spec(
        "# Performance Spec\n\n"
        "## Requirements\n\n"
        "- NFR-001: The system shall respond within the threshold as described above.\n"
    )
    findings = _spec_qvscribe_indirect_reference(spec, CATALOG)
    assert len(findings) == 1
    assert findings[0].pitfall_id == "SPEC-QVSCRIBE-INDIRECT-REFERENCE"


def test_the_above_in_requirement_fires() -> None:
    """'the above' on a normative requirement line → fires."""
    spec = _make_spec(
        "# Upload Spec\n\n"
        "## Requirements\n\n"
        "- FR-010: The system shall validate files using the above criteria.\n"
    )
    findings = _spec_qvscribe_indirect_reference(spec, CATALOG)
    assert len(findings) == 1
    assert findings[0].pitfall_id == "SPEC-QVSCRIBE-INDIRECT-REFERENCE"


def test_multiple_indirect_refs_fires_with_count() -> None:
    """Multiple requirement lines with indirect references → fires once with correct count."""
    spec = _make_spec(
        "# Feature Spec\n\n"
        "## Requirements\n\n"
        "- FR-001: The system shall retry as mentioned above.\n"
        "- FR-002: The service must authenticate users per section 2.\n"
        "- FR-003: The system shall log all events.\n"
    )
    findings = _spec_qvscribe_indirect_reference(spec, CATALOG)
    assert len(findings) == 1
    assert "2" in findings[0].message  # 2 offending lines


def test_refer_to_section_in_requirement_fires() -> None:
    """'refer to section' on a shall line → fires."""
    spec = _make_spec(
        "# Feature Spec\n\n"
        "## Requirements\n\n"
        "- FR-005: The system shall apply the constraints; refer to section 4.1 for the full list.\n"
    )
    findings = _spec_qvscribe_indirect_reference(spec, CATALOG)
    assert len(findings) == 1


def test_finding_anchors_to_first_offending_line() -> None:
    """Finding anchors at the first line with an indirect reference."""
    raw = (
        "# Feature\n\n"
        "## Requirements\n\n"
        "- FR-001: The system shall store data securely.\n"   # line 5, no ref
        "- FR-002: The system shall retry as mentioned above.\n"  # line 6, fires
        "- FR-003: The system shall also comply per section 3.\n"  # line 7, fires
    )
    spec = _make_spec(raw)
    findings = _spec_qvscribe_indirect_reference(spec, CATALOG)
    assert len(findings) == 1
    assert findings[0].line == 6


# ---------------------------------------------------------------------------
# SILENT cases — check must NOT trigger
# ---------------------------------------------------------------------------


def test_well_formed_requirements_no_refs_silent() -> None:
    """Spec with self-contained requirements and no positional references → silent."""
    spec = _make_spec(
        "# Feature Spec\n\n"
        "## Requirements\n\n"
        "- FR-001: The system shall accept PDF input up to 10 MB.\n"
        "- FR-002: The system shall validate the file format against the PDF 1.7 spec.\n"
        "- NFR-001: Response time shall not exceed 200 ms at p95 under 100 req/s.\n"
    )
    findings = _spec_qvscribe_indirect_reference(spec, CATALOG)
    assert findings == []


def test_indirect_ref_in_prose_section_silent() -> None:
    """'as mentioned above' in a non-requirement prose paragraph → silent."""
    spec = _make_spec(
        "# Feature Spec\n\n"
        "## Background\n\n"
        "As mentioned above, the legacy system has performance issues.\n\n"
        "## Requirements\n\n"
        "- FR-001: The system shall authenticate via OAuth 2.0.\n"
    )
    findings = _spec_qvscribe_indirect_reference(spec, CATALOG)
    assert findings == []


def test_see_section_in_fenced_block_silent() -> None:
    """'see section' inside a fenced code block is excluded → silent."""
    spec = _make_spec(
        "# Spec\n\n"
        "## Requirements\n\n"
        "- FR-001: The system shall process requests.\n\n"
        "```markdown\n"
        "FR-002 shall follow — see section 4 for examples.\n"
        "```\n"
    )
    findings = _spec_qvscribe_indirect_reference(spec, CATALOG)
    assert findings == []


def test_see_section_inside_parentheses_silent() -> None:
    """'see section' inside parentheses is a contextual note, not an indirect ref → silent."""
    spec = _make_spec(
        "# Spec\n\n"
        "## Requirements\n\n"
        "- FR-001: The system shall retry up to 3 times with exponential back-off "
        "(see section 4.2 for the retry interval table).\n"
    )
    findings = _spec_qvscribe_indirect_reference(spec, CATALOG)
    assert findings == []


def test_per_section_inside_parentheses_silent() -> None:
    """'per section' inside parentheses on a shall line → silent."""
    spec = _make_spec(
        "# Spec\n\n"
        "## Requirements\n\n"
        "The system shall encrypt data at rest using AES-256 "
        "(per section 5, which cites NIST SP 800-175B).\n"
    )
    findings = _spec_qvscribe_indirect_reference(spec, CATALOG)
    assert findings == []


def test_blockquote_requirement_line_silent() -> None:
    """Requirement line starting with '>' is a blockquote → silent."""
    spec = _make_spec(
        "# Spec\n\n"
        "## Requirements\n\n"
        "> FR-001: The system shall handle errors as mentioned above.\n"
        "- FR-002: The system shall log all events within 1 second.\n"
    )
    findings = _spec_qvscribe_indirect_reference(spec, CATALOG)
    assert findings == []


def test_non_spec_artifact_silent() -> None:
    """Check does not apply to plan artifacts (artifacts=['spec'])."""
    plan = Artifact(
        path="plan.md",
        type=ArtifactType.PLAN,
        raw=(
            "# Implementation Plan\n\n"
            "## Deployment\n\n"
            "Deploy the service as described above.\n"
            "The system shall retry per section 3.\n"
        ),
        sections=parse_sections(
            "# Implementation Plan\n\n"
            "## Deployment\n\n"
            "Deploy the service as described above.\n"
            "The system shall retry per section 3.\n"
        ),
    )
    findings = _spec_qvscribe_indirect_reference(plan, CATALOG)
    assert findings == []


def test_section_word_without_positional_context_silent() -> None:
    """'section' appearing in non-positional context (e.g., 'Requirements Section') → silent."""
    spec = _make_spec(
        "# Feature Spec\n\n"
        "## Requirements\n\n"
        "- FR-001: The system shall support the requirements section format.\n"
        "- FR-002: The system shall validate data as specified in FR-001.\n"
    )
    findings = _spec_qvscribe_indirect_reference(spec, CATALOG)
    assert findings == []


def test_as_per_section_in_parentheses_silent() -> None:
    """'as per section' entirely in parentheses → silent."""
    spec = _make_spec(
        "# Spec\n\n"
        "## Requirements\n\n"
        "- FR-001: The system shall authenticate users via JWT "
        "(as per section 3 of the identity platform guide).\n"
    )
    findings = _spec_qvscribe_indirect_reference(spec, CATALOG)
    assert findings == []
