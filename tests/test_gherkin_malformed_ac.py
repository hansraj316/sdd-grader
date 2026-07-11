"""Tests for SPEC-GHERKIN-MALFORMED-AC: incomplete Given/When/Then triad."""

from __future__ import annotations

import textwrap

import pytest

from sddgrade.catalog import load_catalog
from sddgrade.engine.lint import _spec_checks
from sddgrade.adapters.base import parse_sections
from sddgrade.model import Artifact, ArtifactType


def _spec(raw: str) -> Artifact:
    raw = textwrap.dedent(raw).strip()
    return Artifact(
        path="spec.md",
        type=ArtifactType.SPEC,
        feature_id="test",
        raw=raw,
        sections=parse_sections(raw),
    )


CATALOG = load_catalog()
PITFALL_ID = "SPEC-GHERKIN-MALFORMED-AC"


def _ids(findings):
    return [f.pitfall_id for f in findings]


# ---- full triad passes -------------------------------------------------------

def test_full_gwt_no_finding():
    art = _spec("""
        ## User Story 1
        As a user I want X.

        ### Acceptance Scenarios
        Given the user is logged in
        When they click Submit
        Then the form is saved
    """)
    ids = _ids(_spec_checks(art, CATALOG))
    assert PITFALL_ID not in ids


def test_full_gwt_with_and_continuation():
    """And/But continuations don't affect the triad check."""
    art = _spec("""
        ## User Story 1
        As a user I want X.

        ### Acceptance Scenarios
        Given the user is logged in
        And their session is active
        When they click Submit
        Then the form is saved
        And a confirmation email is sent
    """)
    ids = _ids(_spec_checks(art, CATALOG))
    assert PITFALL_ID not in ids


def test_full_gwt_inline_in_story_body():
    """GWT can appear inside the story body itself (no separate Acceptance section)."""
    art = _spec("""
        ## User Story 2
        As a user I want Y.

        Given the cart has items
        When I press Checkout
        Then an order is created
    """)
    ids = _ids(_spec_checks(art, CATALOG))
    assert PITFALL_ID not in ids


# ---- missing parts fire ---------------------------------------------------------

def test_missing_then_fires():
    art = _spec("""
        ## User Story 1
        As a user I want X.

        ### Acceptance Scenarios
        Given the user is logged in
        When they click Submit
    """)
    ids = _ids(_spec_checks(art, CATALOG))
    assert PITFALL_ID in ids


def test_missing_when_fires():
    art = _spec("""
        ## User Story 1
        As a user I want X.

        ### Acceptance Scenarios
        Given the user is logged in
        Then the form is saved
    """)
    ids = _ids(_spec_checks(art, CATALOG))
    assert PITFALL_ID in ids


def test_missing_given_fires():
    art = _spec("""
        ## User Story 1
        As a user I want X.

        ### Acceptance Scenarios
        When they click Submit
        Then the form is saved
    """)
    ids = _ids(_spec_checks(art, CATALOG))
    assert PITFALL_ID in ids


def test_only_one_keyword_does_not_fire():
    """Single line-leading keyword (prose format '- Given ..., when ..., then ...')
    means formal Gherkin mode is not entered; SPEC-MISSING-ACCEPTANCE handles it."""
    art = _spec("""
        ## User Story 1
        As a user I want X.

        ### Acceptance Scenarios
        Then the form is saved
    """)
    ids = _ids(_spec_checks(art, CATALOG))
    assert PITFALL_ID not in ids


def test_inline_prose_gwt_all_on_one_line_does_not_fire():
    """Inline prose '- Given ..., when ..., then ...' has only Given line-leading;
    formal Gherkin mode requires ≥2 distinct leading keywords."""
    art = _spec("""
        ## User Story 1
        As a user I want X.

        ### Acceptance Scenarios
        - Given the user has items, when they export, then a CSV is produced.
    """)
    ids = _ids(_spec_checks(art, CATALOG))
    assert PITFALL_ID not in ids


# ---- no Gherkin keywords → skip -------------------------------------------------

def test_no_gherkin_keywords_skips():
    """Prose acceptance criteria with no line-leading Given/When/Then are fine."""
    art = _spec("""
        ## User Story 1
        As a user I want X.

        ### Acceptance Scenarios
        - The form validates required fields.
        - Errors are shown inline.
        - Success redirects to dashboard.
    """)
    ids = _ids(_spec_checks(art, CATALOG))
    assert PITFALL_ID not in ids


def test_inline_then_not_line_leading_skips():
    """'then' inside prose (not line-leading) must not trigger the check."""
    art = _spec("""
        ## User Story 1
        As a user I want X.

        ### Acceptance Scenarios
        The system validates inputs and then redirects the user.
    """)
    ids = _ids(_spec_checks(art, CATALOG))
    assert PITFALL_ID not in ids


# ---- finding message quality ---------------------------------------------------

def test_missing_then_message_names_keyword():
    art = _spec("""
        ## User Story 1
        As a user I want X.

        ### Acceptance Scenarios
        Given the user is logged in
        When they click Submit
    """)
    findings = [f for f in _spec_checks(art, CATALOG) if f.pitfall_id == PITFALL_ID]
    assert findings, "expected a finding"
    assert "Then" in findings[0].message


def test_missing_given_message_with_when_then():
    """When+Then line-leading but no Given → formal Gherkin mode (≥2 keywords) → fires."""
    art = _spec("""
        ## User Story 1
        As a user I want X.

        ### Acceptance Scenarios
        When they click Submit
        Then the form is saved
    """)
    findings = [f for f in _spec_checks(art, CATALOG) if f.pitfall_id == PITFALL_ID]
    assert findings
    assert "Given" in findings[0].message


# ---- case-insensitivity --------------------------------------------------------

def test_uppercase_keywords_handled():
    art = _spec("""
        ## User Story 1
        As a user I want X.

        ### Acceptance Scenarios
        GIVEN the user is logged in
        WHEN they click Submit
        THEN the form is saved
    """)
    ids = _ids(_spec_checks(art, CATALOG))
    assert PITFALL_ID not in ids


def test_mixed_case_partial_fires():
    art = _spec("""
        ## User Story 1
        As a user I want X.

        ### Acceptance Scenarios
        GIVEN the user is logged in
        When they click Submit
    """)
    ids = _ids(_spec_checks(art, CATALOG))
    assert PITFALL_ID in ids


# ---- no story sections → no check -------------------------------------------

def test_no_user_story_section_no_check():
    art = _spec("""
        ## Requirements
        FR-001: The system shall do X.

        ## Success Criteria
        - Metric A > 90%
    """)
    ids = _ids(_spec_checks(art, CATALOG))
    assert PITFALL_ID not in ids


# ---- does not fire when SPEC-MISSING-ACCEPTANCE would -------------------------

def test_no_ac_at_all_does_not_also_fire_gherkin():
    """When there is no acceptance section at all, MISSING-ACCEPTANCE fires but not GHERKIN-MALFORMED."""
    art = _spec("""
        ## User Story 1
        As a user I want X.
        The system should respond quickly.
    """)
    ids = _ids(_spec_checks(art, CATALOG))
    assert PITFALL_ID not in ids
    # SPEC-MISSING-ACCEPTANCE should fire instead
    assert "SPEC-MISSING-ACCEPTANCE" in ids
