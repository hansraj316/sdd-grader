"""Tests for SPEC-AC-NO-FR-LINK pitfall.

The check fires when a spec defines both FR-NNN and AC-NNN identifiers but no
single non-fenced line co-references both on the same line.

Guard: only fires when BOTH FR-NNN and AC-NNN identifiers appear in non-fenced
       lines of the spec.  A spec with only FRs, only ACs, or neither is silent.
"""

from __future__ import annotations

import pytest

from sddgrade.adapters.base import parse_sections
from sddgrade.catalog import load_catalog
from sddgrade.engine.lint import _spec_ac_no_fr_link
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


def test_fr_and_ac_on_separate_lines_no_coref_fires() -> None:
    """Spec has FR-001 on one line and AC-001 on another with no co-reference → fires."""
    spec = _make_spec(
        "# Feature Spec\n\n"
        "## Requirements\n\n"
        "- FR-001: The system shall authenticate users via OAuth.\n"
        "- FR-002: The system shall log all authentication events.\n\n"
        "## Acceptance Criteria\n\n"
        "- AC-001: When the user logs in, the system grants a session token.\n"
        "- AC-002: When login fails, an error is returned.\n"
    )
    findings = _spec_ac_no_fr_link(spec, CATALOG)
    assert len(findings) == 1
    assert "SPEC-AC-NO-FR-LINK" in findings[0].pitfall_id
    assert "FR-NNN" in findings[0].message or "FR↔AC" in findings[0].message


def test_multiple_frs_and_acs_no_coref_fires() -> None:
    """Multiple FR-NNN and AC-NNN identifiers spread across the spec with no co-reference → fires."""
    spec = _make_spec(
        "# Spec\n\n"
        "FR-001: The system shall support CSV export.\n"
        "FR-002: The system shall support JSON export.\n\n"
        "AC-001: Exporting 1000 rows produces a file in under 2 s.\n"
        "AC-002: The export file encoding is UTF-8.\n"
    )
    findings = _spec_ac_no_fr_link(spec, CATALOG)
    assert len(findings) == 1


def test_ac_and_fr_in_different_sections_fires() -> None:
    """FR-NNN in Requirements section and AC-NNN in Acceptance section, no co-reference line → fires."""
    spec = _make_spec(
        "# Payment Feature\n\n"
        "## Functional Requirements\n\n"
        "- FR-010: The system shall process payments via Stripe.\n\n"
        "## Acceptance Criteria\n\n"
        "- AC-010: A 200 OK response is returned when payment succeeds.\n"
    )
    findings = _spec_ac_no_fr_link(spec, CATALOG)
    assert len(findings) == 1
    assert findings[0].pitfall_id == "SPEC-AC-NO-FR-LINK"


# ---------------------------------------------------------------------------
# SILENT cases — check must NOT trigger
# ---------------------------------------------------------------------------


def test_coref_on_same_line_silent() -> None:
    """Line contains both FR-001 and AC-001 → co-reference detected, silent."""
    spec = _make_spec(
        "# Feature\n\n"
        "## Requirements\n\n"
        "- FR-001 [AC-001]: The system shall process payments.\n\n"
        "## Acceptance Criteria\n\n"
        "- AC-001: A 200 OK is returned.\n"
    )
    findings = _spec_ac_no_fr_link(spec, CATALOG)
    assert findings == []


def test_ac_references_fr_on_same_line_silent() -> None:
    """AC line explicitly co-references its FR → silent."""
    spec = _make_spec(
        "# Spec\n\n"
        "FR-001: The system shall authenticate users.\n\n"
        "AC-001 [FR-001]: Given valid credentials, the user is granted access.\n"
    )
    findings = _spec_ac_no_fr_link(spec, CATALOG)
    assert findings == []


def test_no_ac_identifiers_silent() -> None:
    """Spec has FR-NNN but no AC-NNN identifiers → guard does not fire, silent."""
    spec = _make_spec(
        "# Spec\n\n"
        "## Requirements\n\n"
        "- FR-001: The system shall authenticate users.\n"
        "- FR-002: The system shall log all events.\n"
    )
    findings = _spec_ac_no_fr_link(spec, CATALOG)
    assert findings == []


def test_no_fr_identifiers_silent() -> None:
    """Spec has AC-NNN but no FR-NNN identifiers → guard does not fire, silent."""
    spec = _make_spec(
        "# Spec\n\n"
        "## Acceptance Criteria\n\n"
        "- AC-001: The user sees the dashboard.\n"
        "- AC-002: An error toast is shown on failure.\n"
    )
    findings = _spec_ac_no_fr_link(spec, CATALOG)
    assert findings == []


def test_neither_fr_nor_ac_silent() -> None:
    """Plain prose spec with no formal IDs → guard does not fire, silent."""
    spec = _make_spec(
        "# Feature\n\n"
        "## Overview\n\n"
        "The user shall be able to log in using their credentials.\n"
    )
    findings = _spec_ac_no_fr_link(spec, CATALOG)
    assert findings == []


def test_coref_in_fenced_block_still_fires() -> None:
    """A co-reference line inside a fenced code block is excluded; finding still fires."""
    spec = _make_spec(
        "# Spec\n\n"
        "FR-001: The system shall generate reports.\n\n"
        "AC-001: The report contains all required columns.\n\n"
        "```\n"
        "# FR-001 AC-001: example in code — excluded\n"
        "```\n"
    )
    findings = _spec_ac_no_fr_link(spec, CATALOG)
    assert len(findings) == 1


def test_nfr_identifier_does_not_count_as_fr_fires() -> None:
    """NFR-NNN identifiers are not FR-NNN; spec with NFR+AC and no FR → guard skips, silent."""
    spec = _make_spec(
        "# Spec\n\n"
        "## Non-Functional Requirements\n\n"
        "- NFR-001: The system shall respond within 200ms.\n\n"
        "## Acceptance Criteria\n\n"
        "- AC-001: p95 latency is below 200ms under 1000 concurrent users.\n"
    )
    # No FR-NNN identifiers → guard does not fire
    findings = _spec_ac_no_fr_link(spec, CATALOG)
    assert findings == []
