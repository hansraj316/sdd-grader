"""Tests for SPEC-GHERKIN-NO-ERROR-SCENARIO pitfall.

Fires when a spec.md has ≥2 formal Gherkin Scenario:/Scenario Outline: blocks
(with at least one When and one Then line) but none of the scenario titles or
Then-clause lines mention error/failure vocabulary.

Sources: MAQA completeness, Canon Volere §5 exception fit criteria,
         ISO/IEC/IEEE 29148:2018 §5.2.5(d) — 'exception behaviors are defined'.
"""
from __future__ import annotations

import textwrap

from sddgrade.adapters.base import parse_sections
from sddgrade.catalog import load_catalog
from sddgrade.engine.lint import _spec_gherkin_no_error_scenario
from sddgrade.model import Artifact, ArtifactType

CATALOG = load_catalog()
PITFALL = "SPEC-GHERKIN-NO-ERROR-SCENARIO"


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
    return [f.pitfall_id for f in _spec_gherkin_no_error_scenario(art, CATALOG)]


# ---------------------------------------------------------------------------
# Silent cases
# ---------------------------------------------------------------------------

def test_silent_no_gherkin():
    """No formal Gherkin → silent."""
    art = _spec("""
        # Spec

        ## FR-001
        The system shall authenticate users.
    """)
    assert _ids(art) == []


def test_silent_one_scenario_only():
    """Only one Scenario block — insufficient for negative-coverage requirement."""
    art = _spec("""
        # Spec

        ## Acceptance Criteria

        Scenario: Successful login
          Given the user is on the login page
          When they enter valid credentials
          Then they are redirected to the dashboard
    """)
    assert _ids(art) == []


def test_silent_error_in_scenario_title():
    """Scenario title contains 'error' — error path covered."""
    art = _spec("""
        # Spec

        ## Acceptance Criteria

        Scenario: Successful login
          Given the user is on the login page
          When they enter valid credentials
          Then they are redirected to the dashboard

        Scenario: Login with invalid credentials shows error
          Given the user is on the login page
          When they enter an invalid password
          Then an error message is displayed
    """)
    assert _ids(art) == []


def test_silent_fail_in_then_clause():
    """Then clause contains 'fail' vocabulary — error path covered."""
    art = _spec("""
        # Spec

        ## Acceptance Criteria

        Scenario: Add item to cart
          Given the user is logged in
          When they click Add to Cart
          Then the item is added to the cart

        Scenario: Checkout with expired card
          Given the user has an expired card on file
          When they complete the checkout
          Then the payment fails with a message
    """)
    assert _ids(art) == []


def test_silent_http_error_status_in_then():
    """Then clause contains HTTP 4xx status code — error path covered."""
    art = _spec("""
        # Spec

        ## Acceptance Criteria

        Scenario: Successful API request
          Given a valid API key
          When the client sends a GET /users request
          Then a 200 response is returned

        Scenario: Unauthorised API request
          Given an invalid API key
          When the client sends a GET /users request
          Then a 401 response is returned
    """)
    assert _ids(art) == []


def test_silent_forbidden_in_title():
    """'forbidden' in scenario title — error path covered."""
    art = _spec("""
        # Spec

        ## Acceptance Criteria

        Scenario: Admin can view user list
          Given the user has admin role
          When they navigate to /admin/users
          Then the user list is displayed

        Scenario: Forbidden for non-admin users
          Given the user has a standard role
          When they navigate to /admin/users
          Then they see a permission-denied page
    """)
    assert _ids(art) == []


def test_silent_no_formal_gherkin_when_only():
    """Has When lines but no Then — not formal Gherkin, silent."""
    art = _spec("""
        # Spec

        Scenario: Login
          Given the user is on the login page
          When they enter credentials

        Scenario: Logout
          Given the user is logged in
          When they click logout
    """)
    assert _ids(art) == []


def test_silent_fenced_block_scenarios():
    """Scenarios inside fenced code block — not counted as formal Gherkin."""
    art = _spec("""
        # Spec

        ```gherkin
        Scenario: Login
          Given the user is on the login page
          When they enter valid credentials
          Then they see the dashboard

        Scenario: Checkout fails
          Given the cart is empty
          When they proceed to checkout
          Then an error is shown
        ```
    """)
    assert _ids(art) == []


def test_silent_plan_artifact():
    """Plan artifact — check applies only to spec."""
    art = _plan("""
        # Plan

        Scenario: Deploy service
          Given the image is built
          When the deployment runs
          Then the service is running

        Scenario: Deploy fails
          Given the image is broken
          When the deployment runs
          Then an error is reported
    """)
    assert _ids(art) == []


def test_silent_rejected_in_then():
    """'rejected' in Then clause — error path covered."""
    art = _spec("""
        # Spec

        ## AC

        Scenario: Valid file upload
          Given a 1MB PNG file
          When the user uploads it
          Then the upload succeeds

        Scenario: Oversized file
          Given a 50MB file
          When the user tries to upload
          Then the upload is rejected with a size-limit message
    """)
    assert _ids(art) == []


# ---------------------------------------------------------------------------
# Fire cases
# ---------------------------------------------------------------------------

def test_fire_all_happy_path_scenarios():
    """Two scenarios, both success paths, no error vocab → fires."""
    art = _spec("""
        # Spec

        ## Acceptance Criteria

        Scenario: Successful login
          Given the user is on the login page
          When they enter valid credentials
          Then they are redirected to the dashboard

        Scenario: Successful logout
          Given the user is logged in
          When they click logout
          Then they see the login page
    """)
    result = _ids(art)
    assert result == [PITFALL]


def test_fire_three_scenarios_no_error_path():
    """Three Scenario blocks with only success vocabulary → fires."""
    art = _spec("""
        # Spec

        Scenario: View product list
          Given the user is on the homepage
          When they browse the catalog
          Then they see the product list

        Scenario: Add item to cart
          Given the user views a product
          When they click Add to Cart
          Then the item count increases

        Scenario: Complete checkout
          Given the user has items in cart
          When they confirm the order
          Then a confirmation email is sent
    """)
    result = _ids(art)
    assert result == [PITFALL]


def test_fire_scenario_outline_no_error():
    """Scenario Outline with ≥2 scenarios and no error vocabulary → fires."""
    art = _spec("""
        # Spec

        Scenario Outline: Search for <term>
          Given the user is on the search page
          When they enter <term>
          Then the results list is displayed

        Scenario: Browse categories
          Given the user is on the homepage
          When they click a category
          Then the filtered results appear
    """)
    result = _ids(art)
    assert result == [PITFALL]


def test_fire_finding_at_line_1():
    """Finding is anchored at line 1 (aggregate structural finding)."""
    art = _spec("""
        # Spec

        Scenario: Login
          Given the user is on the login page
          When they enter valid credentials
          Then they see the dashboard

        Scenario: View profile
          Given the user is logged in
          When they navigate to /profile
          Then the profile page loads
    """)
    findings = _spec_gherkin_no_error_scenario(art, CATALOG)
    assert findings
    assert findings[0].line == 1


def test_fire_only_once():
    """Even with many happy-path scenarios, only one finding is produced."""
    art = _spec("""
        # Spec

        Scenario: Action A
          Given setup A
          When user does A
          Then result A

        Scenario: Action B
          Given setup B
          When user does B
          Then result B

        Scenario: Action C
          Given setup C
          When user does C
          Then result C
    """)
    result = _ids(art)
    assert result == [PITFALL]
