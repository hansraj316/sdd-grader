"""Tests for SPEC-GHERKIN-NO-THEN pitfall.

Fires when a Gherkin scenario block contains at least one When line-leader but
zero Then line-leaders in that same block.  A scenario without a Then step has
no observable assertion and is non-verifiable (MAQA binary-verifiability,
Gherkin Reference §3).

Guard: requires at least one When line-leader AND one Then line-leader anywhere
in the document to enter formal-Gherkin mode.  Documents without a Then
somewhere are skipped (the check is about per-block missing Then, not global
absence — global absence is SPEC-GHERKIN-MALFORMED-AC's territory).

Block boundary reset triggers:
- A "Scenario:" or "Scenario Outline:" heading.
- Two or more consecutive blank lines before the next step.
"""
from __future__ import annotations

import textwrap

from sddgrade.adapters.base import parse_sections
from sddgrade.catalog import load_catalog
from sddgrade.engine.lint import _spec_gherkin_no_then
from sddgrade.model import Artifact, ArtifactType

CATALOG = load_catalog()
PITFALL = "SPEC-GHERKIN-NO-THEN"


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
    return [f.pitfall_id for f in _spec_gherkin_no_then(art, CATALOG)]


# ── fire cases ────────────────────────────────────────────────────────────────

def test_fires_single_block_when_no_then():
    """A scenario block with Given and When but no Then — fires."""
    art = _spec("""
        # Spec

        FR-001 The system shall do X.

        ## Scenario: happy path

        - Given the user is on the login page
        - When the user submits valid credentials

        ## Scenario: complete block

        - Given the system is idle
        - When an event fires
        - Then the counter increments
    """)
    assert _ids(art) == [PITFALL]


def test_fires_second_block_missing_then():
    """First block is complete; second block has When but no Then — fires."""
    art = _spec("""
        # Spec

        FR-001 The system shall handle login.

        ## Scenario: complete

        - Given A
        - When B
        - Then C is visible

        ## Scenario: incomplete

        - Given D
        - When E
    """)
    assert _ids(art) == [PITFALL]


def test_fires_block_separated_by_blank_lines():
    """Block boundary via 2+ blank lines; second block has When but no Then."""
    art = _spec("""
        # Spec

        FR-001 The system shall do Z.

        - Given the user is authenticated
        - When the user clicks delete


        - Given the system is empty
        - When an import completes
        - Then the count is 1
    """)
    assert _ids(art) == [PITFALL]


def test_fires_when_only_block():
    """Block with only a When step (no Given, no Then) — fires."""
    art = _spec("""
        # Spec

        FR-001 The system shall handle events.

        ## Scenario: minimal broken

        - When the timer fires

        ## Scenario: ok

        - Given X
        - When Y fires
        - Then Z is updated
    """)
    assert _ids(art) == [PITFALL]


def test_fires_multiple_blocks_missing_then_one_aggregate():
    """Two blocks both lack Then; one aggregate finding is returned."""
    art = _spec("""
        # Spec

        FR-001 The system shall do A.

        ## Scenario: first

        - Given state is ready
        - When the action is triggered

        ## Scenario: second

        - Given the queue is empty
        - When a message arrives

        ## Scenario: ok

        - Given reference state
        - When reference action
        - Then reference outcome is logged
    """)
    findings = _spec_gherkin_no_then(art, CATALOG)
    assert len(findings) == 1
    assert findings[0].pitfall_id == PITFALL


# ── silent cases ──────────────────────────────────────────────────────────────

def test_silent_no_gherkin_at_all():
    """Document with no Gherkin keywords: formal-Gherkin guard fails — silent."""
    art = _spec("""
        # Spec

        FR-001 The system shall handle requests.
        The user provides input and the system processes it.
    """)
    assert _ids(art) == []


def test_silent_no_when_in_document():
    """Document has Then but no When: guard fails (When required) — silent."""
    art = _spec("""
        # Spec

        FR-001 The system shall display results.

        - Then the page is rendered
    """)
    assert _ids(art) == []


def test_silent_all_blocks_complete():
    """All scenario blocks have Given/When/Then — silent."""
    art = _spec("""
        # Spec

        FR-001 The system shall support login.

        ## Scenario: login success

        - Given the user has valid credentials
        - When the user submits the form
        - Then the dashboard is displayed

        ## Scenario: login failure

        - Given the user has invalid credentials
        - When the user submits the form
        - Then an error message is shown
    """)
    assert _ids(art) == []


def test_silent_inline_gherkin_all_blocks_complete():
    """Inline Gherkin without Scenario: headings — complete block: silent."""
    art = _spec("""
        # Spec

        FR-001 The system shall respond.

        Acceptance criteria:
        - Given the service is healthy
        - When a request arrives
        - Then a 200 response is returned
    """)
    assert _ids(art) == []


def test_silent_plan_artifact():
    """Plan artifacts are not checked — silent regardless of content."""
    art = _plan("""
        # Plan

        ## Scenario: deploy

        - When the deploy completes

        ## Scenario: ok

        - Given the cluster is ready
        - When the pod starts
        - Then health check passes
    """)
    assert _ids(art) == []


def test_silent_fenced_block_excluded():
    """When inside a fenced code block is excluded from scanning — silent."""
    art = _spec("""
        # Spec

        FR-001 The system shall do X.

        ```gherkin
        Scenario: fenced example
          When the user clicks
        ```

        ## Scenario: real

        - Given A
        - When B
        - Then C is updated
    """)
    assert _ids(art) == []


def test_silent_given_only_block():
    """Block with only Given (no When) — check doesn't fire (no When in block)."""
    art = _spec("""
        # Spec

        FR-001 The system shall do X.

        ## Scenario: given-only

        - Given some precondition

        ## Scenario: ok

        - Given A
        - When B fires
        - Then C is set
    """)
    assert _ids(art) == []


def test_silent_scenario_outline_with_then():
    """Scenario Outline with Examples and a Then step — silent."""
    art = _spec("""
        # Spec

        FR-001 The system shall validate input.

        ## Scenario Outline: validation

        - Given the form has <field> set to <value>
        - When the user submits
        - Then <result> is shown

        Examples:
        | field | value | result |
        | email | bad   | error  |
    """)
    assert _ids(art) == []
