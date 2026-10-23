"""Tests for XREF-FR-NO-AC — FR-NNN with no AC-NNN line co-referencing it."""
from __future__ import annotations

import textwrap

import pytest

from sddgrade.adapters.base import parse_sections
from sddgrade.catalog import load_catalog
from sddgrade.engine.lint import _xref_fr_no_ac
from sddgrade.model import Artifact, ArtifactType

CATALOG = load_catalog()
PITFALL = "XREF-FR-NO-AC"


def _spec(raw: str) -> Artifact:
    raw = textwrap.dedent(raw).strip()
    return Artifact(
        path="spec.md",
        type=ArtifactType.SPEC,
        raw=raw,
        sections=parse_sections(raw),
    )


def _run(art: Artifact) -> list:
    return [f for f in _xref_fr_no_ac(art, CATALOG) if f.pitfall_id == PITFALL]


# ─────────────────────────────── fire cases ──────────────────────────────────


def test_single_fr_no_ac_fires():
    """FR-001 exists but no AC line mentions FR-001."""
    art = _spec("""
        # Requirements
        FR-001: The system shall authenticate users via OAuth 2.0.

        ## Acceptance Criteria
        AC-001: Given a valid token, when auth is called, then it returns 200.
    """)
    findings = _run(art)
    assert findings, "Expected XREF-FR-NO-AC to fire"
    assert "FR-001" in findings[0].message
    assert len(findings) == 1


def test_fr002_orphaned_fr001_linked_fires():
    """FR-001 has an AC; FR-002 is orphaned — only FR-002 fires."""
    art = _spec("""
        # Requirements
        FR-001: The system shall list orders newest-first, 20 per page.
        FR-002: The system shall provide a PDF invoice for each order.

        ## Acceptance Criteria
        AC-001 [FR-001]: Given past orders, when I open history, then newest-first.
    """)
    findings = _run(art)
    assert len(findings) == 1
    assert "FR-002" in findings[0].message
    assert "FR-001" not in findings[0].message


def test_multiple_frs_all_orphaned_fires_per_fr():
    """FR-001, FR-002, FR-003 all orphaned — three findings emitted."""
    art = _spec("""
        # Requirements
        FR-001: The system shall do A.
        FR-002: The system shall do B.
        FR-003: The system shall do C.

        ## Acceptance Criteria
        AC-001: Some criterion with no FR tag.
        AC-002: Another criterion also with no FR tag.
    """)
    findings = _run(art)
    assert len(findings) == 3
    ids = {f.message.split()[1].rstrip(":") for f in findings}
    assert ids == {"FR-001", "FR-002", "FR-003"}


def test_two_orphaned_one_linked_fires_two():
    """FR-001 and FR-002 orphaned; FR-003 linked to AC-003 — two findings."""
    art = _spec("""
        # Requirements
        FR-001: The system shall send email notifications.
        FR-002: The system shall support dark mode.
        FR-003: The system shall export data as CSV.

        ## Acceptance Criteria
        AC-001: Some check.
        AC-002: Another check.
        AC-003 [FR-003]: Given data, when exported, then CSV format.
    """)
    findings = _run(art)
    assert len(findings) == 2
    ids = {f.message.split()[1].rstrip(":") for f in findings}
    assert ids == {"FR-001", "FR-002"}


def test_ac_line_without_fr_tag_fires():
    """AC lines exist but none mention FR-001 explicitly."""
    art = _spec("""
        ## Functional Requirements
        FR-001: The system shall validate email format on registration.

        ## Acceptance Criteria
        AC-001: Given a valid email, registration succeeds.
        AC-002: Given an invalid email, an error is shown.
    """)
    findings = _run(art)
    assert findings
    assert any("FR-001" in f.message for f in findings)


# ─────────────────────────────── silent cases ────────────────────────────────


def test_every_fr_has_ac_silent():
    """All FR-NNNs co-referenced on AC lines — no finding."""
    art = _spec("""
        # Requirements
        FR-001: The system shall list orders newest-first.
        FR-002: The system shall provide a PDF invoice.

        ## Acceptance Criteria
        AC-001 [FR-001]: Given past orders, when I open history, then newest-first.
        AC-002 [FR-002]: Given an order, when PDF is requested, then a PDF is returned.
    """)
    findings = _run(art)
    assert not findings


def test_no_fr_ids_silent():
    """Spec has only AC-NNN, no FR-NNN — guard fires, no findings."""
    art = _spec("""
        # Acceptance Criteria
        AC-001: Given a valid token, auth returns 200.
        AC-002: Given an expired token, auth returns 401.
    """)
    findings = _run(art)
    assert not findings


def test_no_ac_ids_silent():
    """Spec has FR-NNN but no AC-NNN anywhere — guard skips."""
    art = _spec("""
        # Requirements
        FR-001: The system shall authenticate users.
        FR-002: The system shall log all access.
    """)
    findings = _run(art)
    assert not findings


def test_fr_in_fenced_block_only_silent():
    """FR-NNN only inside fenced code block — not counted as a live FR identifier."""
    art = _spec("""
        # Overview
        See the requirement reference below.

        ```
        FR-001: The system shall do X.
        ```

        ## Acceptance Criteria
        AC-001: Some criterion.
    """)
    findings = _run(art)
    assert not findings


def test_fr_in_heading_only_silent():
    """FR-NNN only in heading lines — ignored by the check."""
    art = _spec("""
        # Requirements for FR-001 Feature

        The system shall allow users to log in.

        ## Acceptance Criteria
        AC-001: Given credentials, when login is submitted, then access is granted.
    """)
    findings = _run(art)
    assert not findings


def test_inline_fr_tag_on_ac_line_silent():
    """FR-NNN appears inline mid-sentence on an AC line — counts as co-reference."""
    art = _spec("""
        # Requirements
        FR-001: The system shall paginate results to 20 per page.

        ## Acceptance Criteria
        AC-001: Verifies FR-001 — given a search, when results load, then ≤20 shown.
    """)
    findings = _run(art)
    assert not findings


def test_non_spec_artifact_silent():
    """XREF-FR-NO-AC must not fire on a tasks artifact."""
    art = Artifact(
        path="tasks.md",
        type=ArtifactType.TASKS,
        raw="FR-001: shall do X.\nAC-001: some AC.",
        sections=parse_sections("FR-001: shall do X.\nAC-001: some AC."),
    )
    findings = _run(art)
    assert not findings
