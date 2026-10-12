"""Tests for SPEC-FR-COMPOUND pitfall.

A formal requirement line carrying a FR-/NFR- identifier AND two or more
normative modal verbs (shall/must) on the same line violates the ISO 29148
§5.2.5(f) atomicity principle (IBM RQA: one verb per requirement).

FIRE cases: line has (FR|NFR)-NNN AND >=2 shall/must after stripping parenthetical
            citations.
PASS cases: only one modal verb; no FR-/NFR- identifier; non-spec artifact;
            second modal inside parenthetical citation.
"""
from __future__ import annotations

import textwrap

from sddgrade.adapters.base import parse_sections
from sddgrade.catalog import load_catalog
from sddgrade.engine.lint import _spec_fr_compound
from sddgrade.model import Artifact, ArtifactType

CATALOG = load_catalog()
PITFALL = "SPEC-FR-COMPOUND"


def _spec(raw: str) -> Artifact:
    raw = textwrap.dedent(raw).strip()
    return Artifact(
        path="spec.md",
        type=ArtifactType.SPEC,
        feature_id="test",
        raw=raw,
        sections=parse_sections(raw),
    )


def _plan(raw: str) -> Artifact:
    raw = textwrap.dedent(raw).strip()
    return Artifact(
        path="plan.md",
        type=ArtifactType.PLAN,
        feature_id="test",
        raw=raw,
        sections=parse_sections(raw),
    )


def _ids(art: Artifact) -> list[str]:
    return [f.pitfall_id for f in _spec_fr_compound(art, CATALOG)]


# ---------------------------------------------------------------------------
# FIRE cases
# ---------------------------------------------------------------------------

def test_fire_shall_and_shall():
    """FR line with two 'shall' verbs fires."""
    art = _spec("""
        ## Requirements
        - FR-003: The system shall validate inputs and shall log validation failures.
    """)
    assert PITFALL in _ids(art)


def test_fire_shall_and_must():
    """FR line mixing 'shall' and 'must' fires."""
    art = _spec("""
        ## Requirements
        - FR-007: The service shall authenticate users and must authorize each request.
    """)
    assert PITFALL in _ids(art)


def test_fire_nfr_shall_and_must():
    """NFR line with 'shall' and 'must' fires."""
    art = _spec("""
        ## Requirements
        - NFR-002: The API shall respond within 200ms and must support 1000 concurrent users.
    """)
    assert PITFALL in _ids(art)


def test_fire_three_modals():
    """Line with three modal verbs fires."""
    art = _spec("""
        ## Requirements
        - FR-010: The system shall hash passwords, shall salt them, and must store them securely.
    """)
    assert PITFALL in _ids(art)


def test_fire_must_and_must():
    """Two 'must' verbs on an NFR line fires."""
    art = _spec("""
        ## Requirements
        - NFR-005: The cache must expire entries after 5 minutes and must evict on memory pressure.
    """)
    assert PITFALL in _ids(art)


def test_fire_finding_anchored_at_correct_line():
    """Finding is anchored at the offending line number."""
    raw = textwrap.dedent("""
        ## Requirements

        - FR-001: The system shall store user preferences.
        - FR-002: The system shall encrypt data and shall transmit it securely.
        - FR-003: The system shall display a dashboard.
    """).strip()
    art = Artifact(
        path="spec.md",
        type=ArtifactType.SPEC,
        feature_id="test",
        raw=raw,
        sections=parse_sections(raw),
    )
    findings = _spec_fr_compound(art, CATALOG)
    assert findings
    assert findings[0].pitfall_id == PITFALL
    assert findings[0].line is not None
    # The compound line is line 4 (1-indexed, after dedent+strip)
    assert findings[0].line == 4


def test_fire_per_line_two_compounds():
    """Two separate compound lines each produce a finding."""
    art = _spec("""
        ## Requirements
        - FR-001: The system shall validate inputs and shall log errors.
        - FR-002: The system shall encrypt data and must store it securely.
    """)
    findings = _spec_fr_compound(art, CATALOG)
    assert len([f for f in findings if f.pitfall_id == PITFALL]) == 2


# ---------------------------------------------------------------------------
# PASS cases
# ---------------------------------------------------------------------------

def test_pass_single_shall():
    """FR line with only one 'shall' is silent."""
    art = _spec("""
        ## Requirements
        - FR-001: The system shall validate all user inputs.
    """)
    assert PITFALL not in _ids(art)


def test_pass_single_must():
    """NFR line with only one 'must' is silent."""
    art = _spec("""
        ## Requirements
        - NFR-005: The system must achieve 99.9% uptime per calendar month.
    """)
    assert PITFALL not in _ids(art)


def test_pass_no_fr_id_plain_prose():
    """Plain prose with two 'shall' but no FR-/NFR- ID is silent."""
    art = _spec("""
        ## Background
        The system shall follow good practices and shall be maintainable.
    """)
    assert PITFALL not in _ids(art)


def test_pass_non_spec_artifact():
    """Plan artifact never fires regardless of content."""
    art = _plan("""
        ## Deployment Steps
        - FR-003: The service shall deploy and shall scale automatically.
    """)
    assert PITFALL not in _ids(art)


def test_pass_second_modal_in_parens():
    """Second modal inside a parenthetical citation is stripped and does not fire."""
    art = _spec("""
        ## Requirements
        - FR-004: The system shall verify the user's identity (the system must not cache credentials).
    """)
    assert PITFALL not in _ids(art)


def test_pass_fenced_block():
    """Lines inside a fenced code block are excluded."""
    art = _spec("""
        ## Requirements

        - FR-001: The system shall validate inputs.

        ```
        FR-009: The system shall hash passwords and shall salt them.
        ```
    """)
    assert PITFALL not in _ids(art)


def test_pass_no_requirements_at_all():
    """Spec with no requirements section is silent."""
    art = _spec("""
        ## Overview
        This document describes the feature.
    """)
    assert PITFALL not in _ids(art)


def test_pass_nfr_single_modal_with_two_conditions():
    """NFR using 'and' to join conditions but only one modal is silent."""
    art = _spec("""
        ## Requirements
        - NFR-010: The API shall respond within 200ms under normal and peak load conditions.
    """)
    assert PITFALL not in _ids(art)


def test_pass_us_id_not_fr():
    """US- identifiers are not FR/NFR — no trigger even with two modals."""
    art = _spec("""
        ## Requirements
        - US-001: The system shall validate inputs and shall log errors.
    """)
    assert PITFALL not in _ids(art)
