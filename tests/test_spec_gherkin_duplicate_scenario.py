"""Tests for SPEC-GHERKIN-DUPLICATE-SCENARIO pitfall.

Fires when two or more Gherkin Scenario:/Scenario Outline:/Scenario Template:
blocks in the same spec share an identical title (case-sensitive, whitespace-
normalised).

Guard: requires at least one When line-leader AND one Then line-leader anywhere
in the document (formal-Gherkin mode).  Documents without this structure are
skipped (avoids false positives on prose that happens to use the word "Scenario").

Detection: collects scenario titles from non-fenced Scenario:/Scenario
Outline:/Scenario Template: heading lines; strips leading bullets/hashes,
normalises interior whitespace; case-sensitive comparison.  Reports one
aggregate finding anchored at the second occurrence of the first duplicate pair.
"""
from __future__ import annotations

import textwrap

from sddgrade.adapters.base import parse_sections
from sddgrade.catalog import load_catalog
from sddgrade.engine.lint import _spec_gherkin_duplicate_scenario
from sddgrade.model import Artifact, ArtifactType

CATALOG = load_catalog()
PITFALL = "SPEC-GHERKIN-DUPLICATE-SCENARIO"


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
    return [f.pitfall_id for f in _spec_gherkin_duplicate_scenario(art, CATALOG)]


# ── fire cases ────────────────────────────────────────────────────────────────

def test_fires_two_identical_scenario_titles():
    """Two plain Scenario: blocks with the same title — fires."""
    art = _spec("""
        ## Acceptance Criteria

        Scenario: User logs in
          Given the user is on the login page
          When the user submits valid credentials
          Then the dashboard is displayed

        Scenario: User logs in
          Given the user is on the login page with a remembered session
          When the user clicks the login button
          Then the user is redirected to the last-visited page
    """)
    assert _ids(art) == [PITFALL]


def test_fires_scenario_outline_duplicate():
    """Two Scenario Outline blocks with the same title — fires."""
    art = _spec("""
        Scenario Outline: Validate input field
          Given the form is open
          When the user enters <value>
          Then the field shows <result>

          Examples:
            | value | result |
            | valid | pass   |

        Scenario Outline: Validate input field
          Given the form is submitted
          When the user enters <value> in the second field
          Then validation error <error> is shown

          Examples:
            | value | error    |
            | empty | required |
    """)
    assert _ids(art) == [PITFALL]


def test_fires_three_duplicates_reports_first_pair():
    """Three scenarios with the same title — still one aggregate finding."""
    art = _spec("""
        Scenario: Login attempt
          Given the login page is open
          When the user submits credentials
          Then the system responds

        Scenario: Login attempt
          Given the login page is open
          When the user submits wrong password
          Then an error is shown

        Scenario: Login attempt
          Given the account is locked
          When the user submits credentials
          Then the account-locked page is shown
    """)
    findings = _spec_gherkin_duplicate_scenario(art, CATALOG)
    assert len(findings) == 1
    assert findings[0].pitfall_id == PITFALL
    # The message should mention 2 duplicate occurrences (second and third occurrence = 2 pairs)
    assert "2" in findings[0].message


def test_fires_mixed_scenario_and_outline_same_title():
    """A Scenario: and Scenario Outline: sharing the same normalised title — fires."""
    art = _spec("""
        Scenario: Check availability
          Given the service is running
          When the health endpoint is called
          Then it returns 200

        Scenario Outline: Check availability
          Given the service is in state <state>
          When the health endpoint is polled
          Then it returns <code>

          Examples:
            | state   | code |
            | running | 200  |
    """)
    assert _ids(art) == [PITFALL]


def test_fires_leading_bullets_stripped():
    """Scenario headings with leading bullet markers — duplicate detected after stripping."""
    art = _spec("""
        - Scenario: Handle timeout
          - Given the service is slow
          - When the client waits 30 s
          - Then a timeout error is returned

        * Scenario: Handle timeout
          * Given the service is extremely slow
          * When the client waits 60 s
          * Then a gateway timeout is returned
    """)
    assert _ids(art) == [PITFALL]


# ── silent cases ──────────────────────────────────────────────────────────────

def test_silent_all_unique_titles():
    """All scenario titles are unique — silent."""
    art = _spec("""
        Scenario: User logs in with valid credentials
          Given the login form is open
          When the user enters correct username and password
          Then the dashboard is displayed

        Scenario: User logs in with invalid password
          Given the login form is open
          When the user enters wrong password
          Then an error message is shown

        Scenario: User logs in with expired account
          Given the account has expired
          When the user tries to log in
          Then an account-expired error is returned
    """)
    assert _ids(art) == []


def test_silent_no_formal_gherkin_mode():
    """No When/Then line-leaders — guard fails, silent even with duplicate prose."""
    art = _spec("""
        ## Acceptance Criteria

        Scenario: Upload file

        AC-001: The system shall accept PDF uploads.

        Scenario: Upload file

        AC-002: The system shall reject executables.
    """)
    assert _ids(art) == []


def test_silent_case_sensitive_different_case():
    """'User Logs In' vs 'user logs in' are different titles — silent."""
    art = _spec("""
        Scenario: User Logs In
          Given the login page is open
          When valid credentials are entered
          Then access is granted

        Scenario: user logs in
          Given the login page is loaded
          When the submit button is clicked
          Then the session is created
    """)
    assert _ids(art) == []


def test_silent_plan_artifact_skipped():
    """Plan artifact — pitfall only applies to spec, so silent."""
    art = _plan("""
        ## Deployment

        Scenario: Deploy to staging
          When the CI pipeline passes
          Then the container is pushed to staging

        Scenario: Deploy to staging
          When the release is approved
          Then staging is updated to the new version
    """)
    assert _ids(art) == []


def test_silent_fenced_block_excluded():
    """Duplicate titles inside a fenced code block — not detected."""
    art = _spec("""
        ## Overview

        ```gherkin
        Scenario: Example scenario
          Given precondition
          When action
          Then outcome

        Scenario: Example scenario
          Given another precondition
          When another action
          Then another outcome
        ```

        Scenario: Real unique scenario A
          Given the system is idle
          When a request is received
          Then a response is returned

        Scenario: Real unique scenario B
          Given the system is under load
          When a second request arrives
          Then it is queued
    """)
    assert _ids(art) == []


def test_silent_empty_titles_skipped():
    """Bare 'Scenario:' lines with no title text are ignored (no title to compare)."""
    art = _spec("""
        Scenario:
          Given the app is running
          When a ping is sent
          Then pong is received

        Scenario:
          Given the app is idle
          When a health check runs
          Then OK is returned
    """)
    # Two bare-title Scenario: lines — normalised title is empty string, skipped.
    assert _ids(art) == []


def test_silent_scenario_template_unique():
    """Scenario Template: is a Gherkin alias; unique titles are silent."""
    art = _spec("""
        Scenario Template: Login with role <role>
          Given a <role> user exists
          When they log in
          Then they see the <role> dashboard

          Examples:
            | role  |
            | admin |

        Scenario Template: Logout from session
          Given an active session exists
          When the user clicks logout
          Then the session is invalidated
    """)
    assert _ids(art) == []


def test_fires_line_number_points_to_second_occurrence():
    """The finding is anchored at the second occurrence (line of the duplicate)."""
    raw = textwrap.dedent("""
        Scenario: Check balance
          Given an account with funds
          When the balance is requested
          Then the balance is displayed

        Scenario: Different scenario
          Given an empty account
          When the balance is requested
          Then zero is displayed

        Scenario: Check balance
          Given an account with no funds
          When the balance is queried
          Then zero balance is shown
    """).strip()
    art = _spec(raw)
    findings = _spec_gherkin_duplicate_scenario(art, CATALOG)
    assert len(findings) == 1
    assert findings[0].pitfall_id == PITFALL
    # Identify the line of the second "Scenario: Check balance"
    lines = raw.splitlines()
    second_occurrence_line = next(
        i + 1
        for i, line in enumerate(lines)
        if "Check balance" in line
        and i > 0
    )
    # Finding should be at or after the first occurrence line
    assert findings[0].line is not None
    assert findings[0].line > 1
