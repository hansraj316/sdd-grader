"""Tests for SPEC-GHERKIN-MISSING-GIVEN pitfall.

Fires when a Gherkin When line-leader appears in a scenario block that has no
preceding Given line-leader since the last block boundary.

Guard: requires at least one When line-leader AND one Then line-leader in the
document to enter formal-Gherkin mode.  Documents without formal Gherkin are
never checked.

Block boundary reset triggers:
- A "Scenario:" or "Scenario Outline:" heading.
- Two or more consecutive blank lines before the next When.
"""
from __future__ import annotations

import textwrap

from sddgrade.adapters.base import parse_sections
from sddgrade.catalog import load_catalog
from sddgrade.engine.lint import _spec_gherkin_missing_given
from sddgrade.model import Artifact, ArtifactType

CATALOG = load_catalog()
PITFALL = "SPEC-GHERKIN-MISSING-GIVEN"


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
    return [f.pitfall_id for f in _spec_gherkin_missing_given(art, CATALOG)]


# ── fire cases ────────────────────────────────────────────────────────────────

def test_fires_when_without_given_simple():
    """When with no Given at all — fires."""
    art = _spec("""
        ## Acceptance

        - When the user submits payment
        - Then the system shows a confirmation
    """)
    assert PITFALL in _ids(art)


def test_fires_when_before_given_in_same_block():
    """When appears before Given in the block — fires."""
    art = _spec("""
        ## Acceptance

        - When the user clicks submit
        - Given the user is on the checkout page
        - Then the order is saved
    """)
    assert PITFALL in _ids(art)


def test_fires_second_scenario_missing_given():
    """First scenario has Given; second scenario (after Scenario: heading) has no Given — fires."""
    art = _spec("""
        ## Acceptance

        Scenario: successful checkout
        - Given the cart has items
        - When the user clicks checkout
        - Then the order is created

        Scenario: empty cart attempt
        - When the user clicks checkout
        - Then the system shows an error
    """)
    assert PITFALL in _ids(art)


def test_fires_second_block_after_double_blank():
    """Second block (after 2 blank lines) starts with When and no Given — fires."""
    art = _spec("""
        ## Acceptance

        - Given the user is logged in
        - When the user opens the dashboard
        - Then the dashboard loads


        - When the user clicks logout
        - Then the session ends
    """)
    assert PITFALL in _ids(art)


def test_fires_bare_when_then_no_given_anywhere():
    """Document with only When/Then — fires (no Given at all)."""
    art = _spec("""
        ## Acceptance Criteria

        FR-001: The system shall process payments.

        - When payment is submitted
        - Then a receipt is sent
    """)
    assert PITFALL in _ids(art)


def test_fires_multiple_bad_scenarios_anchors_at_first():
    """Multiple scenarios missing Given — finding anchored at first offending When."""
    art = _spec("""
        ## Scenarios

        Scenario: alpha
        - When alpha action happens
        - Then alpha result occurs

        Scenario: beta
        - When beta action happens
        - Then beta result occurs
    """)
    findings = _spec_gherkin_missing_given(art, CATALOG)
    assert any(f.pitfall_id == PITFALL for f in findings)
    # Should fire and carry count in the message
    msgs = [f.message for f in findings if f.pitfall_id == PITFALL]
    assert msgs
    assert "2" in msgs[0]  # two bad When steps


# ── silent cases ──────────────────────────────────────────────────────────────

def test_silent_complete_given_when_then():
    """Complete Given/When/Then — silent."""
    art = _spec("""
        ## Acceptance

        - Given the user is logged in
        - When the user requests a report
        - Then the report is displayed
    """)
    assert PITFALL not in _ids(art)


def test_silent_given_then_when_ordering_given_before_when():
    """Given appears before When, even if Then comes after When — silent (Given is present)."""
    art = _spec("""
        ## Acceptance

        - Given the cart is populated
        - When checkout is initiated
        - Then payment is processed
    """)
    assert PITFALL not in _ids(art)


def test_silent_no_formal_gherkin_no_then():
    """No Then line-leader — not in formal Gherkin mode, silent."""
    art = _spec("""
        ## Requirements

        FR-001: The system shall allow users to log in.
        When a user provides valid credentials they get access.
        Given constraints exist.
    """)
    assert PITFALL not in _ids(art)


def test_silent_no_formal_gherkin_no_when():
    """No When line-leader — not in formal Gherkin mode, silent."""
    art = _spec("""
        ## Acceptance

        - Given the user is authenticated
        - Then the dashboard is visible
    """)
    assert PITFALL not in _ids(art)


def test_silent_second_scenario_has_given():
    """Both scenarios have Given — silent."""
    art = _spec("""
        ## Acceptance

        Scenario: happy path
        - Given the user is logged in
        - When the user submits the form
        - Then data is saved

        Scenario: validation failure
        - Given the form has invalid data
        - When the user submits the form
        - Then an error message is shown
    """)
    assert PITFALL not in _ids(art)


def test_silent_plan_artifact_not_checked():
    """Plan artifact — check does not apply, silent."""
    art = _plan("""
        ## Deployment

        - When deploying the service
        - Then health checks must pass
    """)
    assert PITFALL not in _ids(art)


def test_silent_given_in_fenced_block_does_not_count_when_outside():
    """Given only inside a fenced code block is excluded; When outside fires."""
    art = _spec("""
        ## Acceptance

        Example:
        ```gherkin
        Given the user is on the page
        When the user clicks submit
        Then the form is saved
        ```

        - When the user clicks cancel
        - Then the modal closes
    """)
    # The When/Then outside the fence exist, so formal Gherkin mode is entered.
    # No Given outside the fence, so the When outside fires.
    assert PITFALL in _ids(art)


def test_silent_and_after_given_counts_as_given_block():
    """And/But after Given do not break the Given-block state — subsequent When is silent."""
    art = _spec("""
        ## Acceptance

        - Given the user is authenticated
        - And the user has admin privileges
        - When the user accesses the admin panel
        - Then the admin dashboard loads
    """)
    assert PITFALL not in _ids(art)
