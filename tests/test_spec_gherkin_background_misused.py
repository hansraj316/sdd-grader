"""Tests for SPEC-GHERKIN-BACKGROUND-MISUSED pitfall.

Fires when a Gherkin Background block contains a When or Then step-leader.
Gherkin spec: Background may only hold Given (precondition) steps.

Guard: at least one non-fenced 'Background:' heading in the document AND
formal-Gherkin mode (at least one When line-leader AND one Then line-leader
anywhere in the document).

Block boundary reset: a Scenario:/Scenario Outline:/Scenario Template: heading,
or 2+ consecutive blank lines.
"""
from __future__ import annotations

import textwrap

from sddgrade.adapters.base import parse_sections
from sddgrade.catalog import load_catalog
from sddgrade.engine.lint import _spec_gherkin_background_misused
from sddgrade.model import Artifact, ArtifactType

CATALOG = load_catalog()
PITFALL = "SPEC-GHERKIN-BACKGROUND-MISUSED"


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
    return [f.pitfall_id for f in _spec_gherkin_background_misused(art, CATALOG)]


# ── fire cases ────────────────────────────────────────────────────────────────

def test_fires_when_in_background():
    """Background block has a When step — fires."""
    art = _spec("""
        # Spec

        FR-001 The system shall support login.

        ## Background:

        - Given the app is running
        - When the user navigates to the login page

        ## Scenario: login success

        - Given valid credentials are entered
        - When the user clicks submit
        - Then the dashboard is shown
    """)
    assert _ids(art) == [PITFALL]


def test_fires_then_in_background():
    """Background block has a Then step — fires."""
    art = _spec("""
        # Spec

        FR-001 The system shall render the homepage.

        Background:

        - Given the server is running
        - Then the status page returns 200

        Scenario: view homepage

        - Given the user is not logged in
        - When the user visits /
        - Then the landing page is shown
    """)
    assert _ids(art) == [PITFALL]


def test_fires_when_and_then_in_background():
    """Background block has both When and Then — fires once (aggregate)."""
    art = _spec("""
        # Spec

        FR-001 The system shall handle requests.

        ## Background:

        - Given the database is seeded
        - When the cache is primed
        - Then the response cache is warm

        ## Scenario: fast read

        - Given a request for /items
        - When the cache is hit
        - Then response time is under 50ms
    """)
    findings = _spec_gherkin_background_misused(art, CATALOG)
    assert len(findings) == 1
    assert findings[0].pitfall_id == PITFALL


def test_fires_only_when_in_background_no_given():
    """Background block with When but no Given — fires."""
    art = _spec("""
        # Spec

        FR-001 The system shall process data.

        Background:

        - When the scheduler fires

        Scenario: process batch

        - Given a queue of 10 items
        - When the worker polls
        - Then all items are processed
    """)
    assert _ids(art) == [PITFALL]


def test_fires_inline_gherkin_background():
    """Background: heading (non-markdown heading) with When — fires."""
    art = _spec("""
        # Spec

        FR-001 The system shall authenticate.

        Background:
        Given the auth service is up
        When a token is issued

        Scenario: access protected resource
        Given a valid token
        When the user requests /api/me
        Then a 200 response is returned
    """)
    assert _ids(art) == [PITFALL]


# ── silent cases ──────────────────────────────────────────────────────────────

def test_silent_no_background_heading():
    """No Background: heading — guard fails, silent."""
    art = _spec("""
        # Spec

        FR-001 The system shall handle login.

        ## Scenario: success

        - Given valid credentials
        - When the user logs in
        - Then the dashboard is shown
    """)
    assert _ids(art) == []


def test_silent_background_only_given_steps():
    """Background has only Given steps — silent."""
    art = _spec("""
        # Spec

        FR-001 The system shall manage accounts.

        ## Background:

        - Given the database is clean
        - Given an admin user exists

        ## Scenario: create account

        - Given a new user form
        - When the admin submits
        - Then the account is created
    """)
    assert _ids(art) == []


def test_silent_background_only_given_and_but():
    """Background with Given and But steps — silent (And/But are Given continuations)."""
    art = _spec("""
        # Spec

        FR-001 The system shall validate access.

        Background:

        - Given the server is running
        - And the feature flag is enabled

        Scenario: authorised access

        - Given a logged-in admin
        - When the admin accesses /admin
        - Then the page is rendered
    """)
    assert _ids(art) == []


def test_silent_no_formal_gherkin_mode():
    """Document has Background: but no When or Then anywhere — guard fails, silent."""
    art = _spec("""
        # Spec

        FR-001 The system shall process inputs.

        Background:

        - When the scheduler fires

        Acceptance criteria:
        Some prose about expected behavior.
    """)
    assert _ids(art) == []


def test_silent_plan_artifact():
    """Plan artifacts are not checked — silent regardless of content."""
    art = _plan("""
        # Plan

        Background:

        - When the deploy script runs
        - Then pods restart

        Scenario: verify

        - Given the cluster is up
        - When health checks pass
        - Then traffic is routed
    """)
    assert _ids(art) == []


def test_silent_fenced_background_excluded():
    """Background: heading inside a fenced code block — excluded, silent."""
    art = _spec("""
        # Spec

        FR-001 The system shall handle events.

        ```gherkin
        Background:
          When something happens
        ```

        ## Scenario: real

        - Given A
        - When B fires
        - Then C is logged
    """)
    assert _ids(art) == []


def test_silent_when_after_scenario_not_background():
    """When step follows a Scenario heading (not Background) — silent."""
    art = _spec("""
        # Spec

        FR-001 The system shall respond.

        ## Background:

        - Given the service is started

        ## Scenario: normal

        - Given a user request
        - When the endpoint is called
        - Then a 200 is returned
    """)
    assert _ids(art) == []


def test_fires_reports_line_of_first_offending_step():
    """The finding is anchored at the first When/Then line in Background."""
    raw = textwrap.dedent("""
        # Spec

        FR-001 The system shall do X.

        Background:

        - Given the setup is done
        - When the trigger fires

        Scenario: check

        - Given state A
        - When action B
        - Then result C
    """).strip()
    art = Artifact(
        path="spec.md",
        type=ArtifactType.SPEC,
        feature_id="test",
        raw=raw,
        sections=parse_sections(raw),
    )
    findings = _spec_gherkin_background_misused(art, CATALOG)
    assert len(findings) == 1
    assert findings[0].pitfall_id == PITFALL
    # The When step should be around line 9
    assert findings[0].line is not None
    assert findings[0].line > 1
