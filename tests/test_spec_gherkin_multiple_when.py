"""Tests for SPEC-GHERKIN-MULTIPLE-WHEN pitfall.

Fires when a formal Gherkin scenario block contains two or more When line-leaders.

Guard: requires at least one When AND one Then line-leader in the document
(formal-Gherkin mode).  Documents without formal Gherkin are never checked.

Block boundary reset triggers:
- A "Scenario:" or "Scenario Outline:" heading.
- Two or more consecutive blank lines before the next When.

One aggregate finding is emitted per offending block, anchored at the first
offending second-When line.
"""
from __future__ import annotations

import textwrap

from sddgrade.adapters.base import parse_sections
from sddgrade.catalog import load_catalog
from sddgrade.engine.lint import _spec_gherkin_multiple_when
from sddgrade.model import Artifact, ArtifactType

CATALOG = load_catalog()
PITFALL = "SPEC-GHERKIN-MULTIPLE-WHEN"


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
    return [f.pitfall_id for f in _spec_gherkin_multiple_when(art, CATALOG)]


# ── fire cases ────────────────────────────────────────────────────────────────

def test_fires_two_when_in_same_block():
    """Two When steps in a single scenario block — fires."""
    art = _spec("""
        ## Acceptance

        - Given the user is logged in
        - When the user clicks Save
        - When the user refreshes the page
        - Then the data is persisted
    """)
    assert PITFALL in _ids(art)


def test_fires_three_when_in_same_block():
    """Three When steps in one block — fires once (aggregate)."""
    art = _spec("""
        ## Acceptance

        - Given the user is on the dashboard
        - When the user clicks Export
        - When the user selects CSV
        - When the user confirms
        - Then the file is downloaded
    """)
    findings = _spec_gherkin_multiple_when(art, CATALOG)
    assert any(f.pitfall_id == PITFALL for f in findings)


def test_fires_no_scenario_heading_double_when():
    """Document with no Scenario: heading but 2 When steps in one block — fires."""
    art = _spec("""
        ## Acceptance Criteria

        - Given the cart has 3 items
        - When the user applies a coupon
        - When the user proceeds to checkout
        - Then the discount is applied
    """)
    assert PITFALL in _ids(art)


def test_fires_scenario_heading_second_block_double_when():
    """First block is fine; second block (after Scenario: heading) has 2 When — fires."""
    art = _spec("""
        Scenario: Single action

        - Given the user is authenticated
        - When the user views the profile
        - Then the profile is shown

        Scenario: Compound action

        - Given the user is on the settings page
        - When the user changes the email
        - When the user changes the password
        - Then the settings are saved
    """)
    assert PITFALL in _ids(art)


def test_fires_blank_line_reset_second_block_double_when():
    """After 2 blank lines (block reset), second block has 2 When — fires."""
    art = _spec("""
        ## Acceptance

        - Given the user is logged in
        - When the user opens the menu
        - Then the menu is visible


        - Given the user is on the edit page
        - When the user clicks Update
        - When the user clicks Publish
        - Then the item is published
    """)
    assert PITFALL in _ids(art)


# ── silent cases ──────────────────────────────────────────────────────────────

def test_silent_single_when_per_block():
    """Each block has exactly one When — silent."""
    art = _spec("""
        ## Acceptance

        - Given the user is logged in
        - When the user clicks Save
        - Then the data is persisted
    """)
    assert PITFALL not in _ids(art)


def test_silent_separate_blocks_each_one_when():
    """Two separate Scenario blocks each with one When — silent."""
    art = _spec("""
        Scenario: Save

        - Given the user has edited the form
        - When the user clicks Save
        - Then the form is saved

        Scenario: Discard

        - Given the user has edited the form
        - When the user clicks Discard
        - Then the changes are discarded
    """)
    assert PITFALL not in _ids(art)


def test_silent_no_formal_gherkin():
    """No When/Then line-leaders at all — guard fails, silent."""
    art = _spec("""
        ## Requirements

        FR-001: The system shall store user preferences.
        NFR-001: Response time shall be under 200 ms.
    """)
    assert PITFALL not in _ids(art)


def test_silent_no_then():
    """When present but no Then — guard fails (not formal-Gherkin mode), silent."""
    art = _spec("""
        ## Acceptance

        - Given the user is on the page
        - When the user clicks the button
        - And the action completes
    """)
    assert PITFALL not in _ids(art)


def test_silent_fenced_when_lines():
    """When lines inside fenced code block are excluded — silent."""
    art = _spec("""
        ## Acceptance

        - Given the user is authenticated
        - When the user calls the API
        - Then the response is 200

        ```gherkin
        When the user clicks Save
        When the user refreshes
        Then the data is shown
        ```
    """)
    assert PITFALL not in _ids(art)


def test_silent_plan_artifact():
    """Pitfall only applies to spec artifacts — plan is always silent."""
    art = _plan("""
        ## Deployment

        - Given the cluster is healthy
        - When the deploy runs
        - When the health check fires
        - Then the service is live
    """)
    assert PITFALL not in _ids(art)


def test_silent_two_when_in_two_separate_blocks_via_heading():
    """Each Scenario: block has only one When — silent even with two blocks."""
    art = _spec("""
        Scenario: Login

        - Given the user provides credentials
        - When the user submits the login form
        - Then the user is redirected to the dashboard

        Scenario: Logout

        - Given the user is authenticated
        - When the user clicks Logout
        - Then the session is terminated
    """)
    assert PITFALL not in _ids(art)


def test_silent_two_when_in_two_separate_blocks_via_blank_lines():
    """Two blocks separated by 2 blank lines each have one When — silent."""
    art = _spec("""
        ## AC-001

        - Given the user is on the search page
        - When the user types a query
        - Then results are displayed


        - Given the results are displayed
        - When the user clicks a result
        - Then the detail page is shown
    """)
    assert PITFALL not in _ids(art)
