"""Tests for the SPEC-REQ-SECTION-PROSE-ONLY pitfall (requirements section with prose but no normative statements)."""
from __future__ import annotations

import textwrap

from sddgrade.adapters.base import parse_sections
from sddgrade.catalog import load_catalog
from sddgrade.engine.lint import _req_section_prose_only
from sddgrade.model import Artifact, ArtifactType

CATALOG = load_catalog()
PITFALL = "SPEC-REQ-SECTION-PROSE-ONLY"


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
    return [f.pitfall_id for f in _req_section_prose_only(art, CATALOG)]


# ── fires cases ───────────────────────────────────────────────────────────────

def test_requirements_section_prose_only():
    """Requirements section with prose but no normative statements fires."""
    art = _spec("""
        ## Requirements

        The export feature allows users to download their data as CSV.
        Authentication is handled by the existing session mechanism.
    """)
    assert PITFALL in _ids(art)


def test_functional_requirements_section_prose_only():
    """Functional Requirements section with prose but no shall/must/IDs fires."""
    art = _spec("""
        ## Functional Requirements

        Authentication is handled by OAuth. Sessions expire after 24 hours.
        The user can access their profile from the dashboard.
    """)
    assert PITFALL in _ids(art)


def test_requirements_section_no_ids_no_modals():
    """Section with only descriptive prose and no FR-/NFR- IDs fires."""
    art = _spec("""
        ## Requirements

        The system integrates with a third-party payment gateway.
        Users receive email confirmation after each transaction.
        The dashboard displays recent activity in real time.
    """)
    assert PITFALL in _ids(art)


def test_fires_on_standalone_requirements_heading():
    """Standalone '## Requirements' heading with prose fires."""
    art = _spec("""
        ## Overview

        This spec covers the CSV export feature.

        ## Requirements

        The export feature allows users to download their data as CSV.
        The download should be triggered from the user profile page.
    """)
    assert PITFALL in _ids(art)


def test_fires_reports_section_title_in_message():
    """The finding message includes the section title."""
    art = _spec("""
        ## Requirements

        The system handles user authentication via sessions.
    """)
    findings = _req_section_prose_only(art, CATALOG)
    assert findings
    assert "Requirements" in findings[0].message


# ── no-fire cases ─────────────────────────────────────────────────────────────

def test_no_fire_when_shall_present():
    """Section with 'shall' in body does not fire."""
    art = _spec("""
        ## Requirements

        The system shall generate reports on demand.
    """)
    assert PITFALL not in _ids(art)


def test_no_fire_when_must_present():
    """Section with 'must' in body does not fire."""
    art = _spec("""
        ## Requirements

        Users must authenticate before accessing the dashboard.
    """)
    assert PITFALL not in _ids(art)


def test_no_fire_when_fr_id_present():
    """Section with FR-N ID does not fire."""
    art = _spec("""
        ## Requirements

        FR-001: The system shall authenticate users via OAuth 2.0.
    """)
    assert PITFALL not in _ids(art)


def test_no_fire_when_nfr_id_present():
    """Section with NFR-N ID does not fire."""
    art = _spec("""
        ## Functional Requirements

        NFR-01: The API shall respond within 200ms at p95.
    """)
    assert PITFALL not in _ids(art)


def test_no_fire_when_ac_id_present():
    """Section with AC-N ID does not fire."""
    art = _spec("""
        ## Requirements

        AC-01: Given logged in, when the user clicks export, the CSV shall download.
    """)
    assert PITFALL not in _ids(art)


def test_no_fire_when_us_id_present():
    """Section with US-N ID does not fire."""
    art = _spec("""
        ## Requirements

        US-01: As a user I want to export data so that I can analyse it offline.
    """)
    assert PITFALL not in _ids(art)


def test_no_fire_body_too_short():
    """Section body shorter than 30 chars does not fire."""
    art = _spec("""
        ## Requirements

        TBD
    """)
    assert PITFALL not in _ids(art)


def test_no_fire_non_requirements_section_title():
    """Section titled 'Overview' does not fire even with pure prose."""
    art = _spec("""
        ## Overview

        This section describes the feature at a high level.
        It covers the main flows and edge cases.
    """)
    assert PITFALL not in _ids(art)


def test_no_fire_plan_artifact():
    """Does not fire on plan.md (applies to spec only)."""
    plan = _plan("""
        ## Requirements

        The deployment uses blue-green switching to minimise downtime.
        No normative statements are needed in a plan requirements note.
    """)
    assert PITFALL not in _ids(plan)


def test_no_fire_fenced_code_block_excluded():
    """Normative keywords inside a fenced code block are not counted as indicators."""
    art = _spec("""
        ## Requirements

        The authentication component works as follows.

        ```python
        # shall and must appear here but are code, not requirements
        if user.must_change_password:
            redirect()
        ```

        The user is redirected to the change-password screen.
    """)
    # The prose body (excluding fenced block) has no normative modal — should fire.
    assert PITFALL in _ids(art)


def test_no_fire_when_shall_outside_fenced_block():
    """'shall' outside a fenced block does prevent firing."""
    art = _spec("""
        ## Requirements

        The system shall redirect users to change-password screen.

        ```python
        # implementation note
        if user.must_change_password:
            redirect()
        ```
    """)
    assert PITFALL not in _ids(art)
