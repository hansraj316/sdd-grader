"""Tests for SPEC-GHERKIN-THEN-WITHOUT-WHEN pitfall.

Fires when a Gherkin scenario block has a Then assertion step but no When
trigger step in the same block.

Guard: at least one Then line-leader present in the document (formal-Gherkin mode).

Block boundaries:
- A "Scenario:" or "Scenario Outline:" heading.
- Two or more consecutive blank lines.
"""
from __future__ import annotations

import textwrap

from sddgrade.adapters.base import parse_sections
from sddgrade.catalog import load_catalog
from sddgrade.engine.lint import _spec_gherkin_then_without_when
from sddgrade.model import Artifact, ArtifactType

CATALOG = load_catalog()
PITFALL = "SPEC-GHERKIN-THEN-WITHOUT-WHEN"


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
    return [f.pitfall_id for f in _spec_gherkin_then_without_when(art, CATALOG)]


# ── fire cases ────────────────────────────────────────────────────────────────

def test_fires_given_then_no_when():
    """Given + Then but no When → fires."""
    art = _spec("""
        ## Acceptance

        Scenario: Payment confirmation
          Given the user has items in the cart
          Then the system shows a confirmation
    """)
    assert PITFALL in _ids(art)


def test_fires_only_then_no_given_no_when():
    """Only Then (no Given, no When) → fires."""
    art = _spec("""
        ## Acceptance

        Scenario: Order placed
          Then the order is confirmed
    """)
    assert PITFALL in _ids(art)


def test_fires_scenario_outline_then_no_when():
    """Scenario Outline with Then but no When → fires."""
    art = _spec("""
        ## Acceptance

        Scenario Outline: Status check
          Given the user is logged in as <role>
          Then the user sees the <dashboard>

        Examples:
          | role  | dashboard |
          | admin | admin     |
    """)
    assert PITFALL in _ids(art)


def test_fires_second_block_missing_when():
    """First block is complete; second block missing When → fires for second block."""
    art = _spec("""
        ## Acceptance

        Scenario: Login succeeds
          Given the user is on the login page
          When the user submits valid credentials
          Then the user is redirected to the dashboard

        Scenario: Profile visible
          Given the user is logged in
          Then the user sees their profile
    """)
    ids = _ids(art)
    assert PITFALL in ids


def test_fires_block_separated_by_blank_lines():
    """Block with Then but no When, separated from prior block by 2 blank lines → fires."""
    art = _spec("""
        ## Acceptance

        - When the user pays
        - Then the receipt is emailed


        - Given the invoice is generated
        - Then the invoice is stored
    """)
    ids = _ids(art)
    assert PITFALL in ids


def test_fires_anchored_at_first_then_line():
    """Finding is anchored at the first Then line in the offending block."""
    art = _spec("""
        ## Acceptance

        Scenario: State check
          Given the system is idle
          Then the status is idle
          Then the queue is empty
    """)
    findings = _spec_gherkin_then_without_when(art, CATALOG)
    assert any(f.pitfall_id == PITFALL for f in findings)
    # Finding should be on the first Then line (not the second)
    fire_lines = [f.line for f in findings if f.pitfall_id == PITFALL]
    assert fire_lines[0] < max(fire_lines) or len(fire_lines) == 1


# ── silent cases ──────────────────────────────────────────────────────────────

def test_silent_complete_given_when_then():
    """Complete Given + When + Then scenario → no finding."""
    art = _spec("""
        ## Acceptance

        Scenario: Successful purchase
          Given the user has items in their cart
          When the user submits payment
          Then the system shows a confirmation message
    """)
    assert PITFALL not in _ids(art)


def test_silent_when_then_no_given():
    """When + Then without Given (different check: SPEC-GHERKIN-MISSING-GIVEN) → no finding here."""
    art = _spec("""
        ## Acceptance

        Scenario: State transition
          When the user clicks Submit
          Then the form is saved
    """)
    assert PITFALL not in _ids(art)


def test_silent_no_gherkin_structure():
    """Non-Gherkin spec with no Then line-leader → no finding."""
    art = _spec("""
        ## Requirements

        FR-001: The system shall allow user login.
        FR-002: The system shall display a dashboard.
    """)
    assert PITFALL not in _ids(art)


def test_silent_fenced_then_no_when():
    """Then without When inside a fenced block → no finding."""
    art = _spec("""
        ## Example

        ```gherkin
        Scenario: Fenced
          Given something
          Then the result is shown
        ```
    """)
    assert PITFALL not in _ids(art)


def test_silent_plan_artifact():
    """Plan artifact → no finding (spec-only check)."""
    art = _plan("""
        ## Deployment

        - Then the service is live
        - Given env is set
    """)
    assert PITFALL not in _ids(art)


def test_silent_multiple_complete_scenarios():
    """Multiple complete scenarios → no finding."""
    art = _spec("""
        ## Acceptance

        Scenario: Login
          Given the user is on the login page
          When the user enters credentials
          Then the user is logged in

        Scenario: Logout
          Given the user is logged in
          When the user clicks Logout
          Then the user is redirected to the home page
    """)
    assert PITFALL not in _ids(art)


def test_silent_when_then_and_continuation():
    """When + Then + And continuation → no finding."""
    art = _spec("""
        ## Acceptance

        Scenario: Order placed
          Given the user has items in cart
          When the user confirms the order
          Then the order is created
          And the user receives a confirmation email
    """)
    assert PITFALL not in _ids(art)


def test_silent_no_then_at_all():
    """Document with no Then line-leader at all → guard fails → no finding."""
    art = _spec("""
        ## Acceptance

        Scenario: Action
          Given the system is running
          When the user triggers an event
    """)
    assert PITFALL not in _ids(art)
