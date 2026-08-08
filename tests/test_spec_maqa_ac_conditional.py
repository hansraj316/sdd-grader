"""Tests for SPEC-MAQA-AC-CONDITIONAL pitfall.

Fires when a Gherkin Then clause (in formal-Gherkin mode) contains conditional
language (if/unless/depending/provided that/in the event) or non-normative modals
(should/may/might/could) that make the step non-binary.

Guard: requires both a Given line-leader AND a When line-leader to enter
formal-Gherkin mode.  Prose ACs are never subject to this check.
"""
from __future__ import annotations

import textwrap

from sddgrade.adapters.base import parse_sections
from sddgrade.catalog import load_catalog
from sddgrade.engine.lint import _spec_maqa_ac_conditional
from sddgrade.model import Artifact, ArtifactType

CATALOG = load_catalog()
PITFALL = "SPEC-MAQA-AC-CONDITIONAL"


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
    return [f.pitfall_id for f in _spec_maqa_ac_conditional(art, CATALOG)]


# ── fire cases ────────────────────────────────────────────────────────────────

def test_fires_should_in_then_clause():
    """'should' in Then clause makes the step optional — fires."""
    art = _spec("""
        ## Acceptance

        - Given the user submits payment
        - When the transaction is processed
        - Then the user should receive a confirmation email
    """)
    assert PITFALL in _ids(art)


def test_fires_may_in_then_clause():
    """'may' in Then clause makes the step optional — fires."""
    art = _spec("""
        ## Acceptance

        - Given the user uploads a file
        - When the upload completes
        - Then the system may display a success notification
    """)
    assert PITFALL in _ids(art)


def test_fires_might_in_then_clause():
    """'might' in Then clause makes the step optional — fires."""
    art = _spec("""
        ## Acceptance

        - Given a background job runs
        - When it encounters a transient error
        - Then it might retry the operation
    """)
    assert PITFALL in _ids(art)


def test_fires_could_in_then_clause():
    """'could' in Then clause makes the step optional — fires."""
    art = _spec("""
        ## Acceptance

        - Given an admin is logged in
        - When an alert threshold is exceeded
        - Then the dashboard could highlight the offending metric
    """)
    assert PITFALL in _ids(art)


def test_fires_if_conditional_in_then_clause():
    """'if' in Then clause makes the outcome conditional — fires."""
    art = _spec("""
        ## Acceptance

        - Given a payment is submitted
        - When the card is charged
        - Then the user should receive a confirmation email if payment succeeds
    """)
    assert PITFALL in _ids(art)


def test_fires_unless_conditional_in_then_clause():
    """'unless' in Then clause makes the outcome conditional — fires."""
    art = _spec("""
        ## Acceptance

        - Given the session timer is running
        - When the user is idle
        - Then the session is terminated unless the user interacts
    """)
    assert PITFALL in _ids(art)


def test_fires_depending_conditional_in_then_clause():
    """'depending' in Then clause makes the outcome conditional — fires."""
    art = _spec("""
        ## Acceptance

        - Given a user requests deletion
        - When the request is received
        - Then the record may be deleted depending on permissions
    """)
    assert PITFALL in _ids(art)


def test_fires_provided_that_conditional_in_then_clause():
    """'provided that' in Then clause makes the outcome conditional — fires."""
    art = _spec("""
        ## Acceptance

        - Given the integration is active
        - When a sync is triggered
        - Then the data is pushed provided that the API is reachable
    """)
    assert PITFALL in _ids(art)


def test_fires_multiple_offending_then_clauses_reports_first():
    """Multiple offending Then clauses emit one finding anchored at the first."""
    art = _spec("""
        ## Acceptance

        - Given a user logs in
        - When valid credentials are provided
        - Then the session should be established

        - Given a user logs out
        - When the logout action is triggered
        - Then the session may be invalidated
    """)
    findings = _spec_maqa_ac_conditional(art, CATALOG)
    assert len(findings) == 1
    assert PITFALL in findings[0].pitfall_id


# ── silent cases ──────────────────────────────────────────────────────────────

def test_silent_binary_then_clause():
    """Binary, unconditional Then clause does not fire."""
    art = _spec("""
        ## Acceptance

        - Given the user submits valid payment details
        - When the transaction is processed
        - Then a 200 OK response is returned and the order status is set to confirmed
    """)
    assert PITFALL not in _ids(art)


def test_silent_binary_then_with_observable_state():
    """Concrete observable assertion without modals or conditionals is silent."""
    art = _spec("""
        ## Acceptance

        - Given a user requests account deletion
        - When the request is confirmed
        - Then the account is deleted and a confirmation email is sent to the registered address
    """)
    assert PITFALL not in _ids(art)


def test_silent_no_given_leader_no_gherkin_mode():
    """Without a Given line-leader the check does not enter Gherkin mode."""
    art = _spec("""
        ## Acceptance

        - When the user clicks submit
        - Then the system should save the record
    """)
    assert PITFALL not in _ids(art)


def test_silent_no_when_leader_no_gherkin_mode():
    """Without a When line-leader the check does not enter Gherkin mode."""
    art = _spec("""
        ## Acceptance

        - Given the user is authenticated
        - Then the system should display the dashboard
    """)
    assert PITFALL not in _ids(art)


def test_silent_conditional_in_given_not_then():
    """Conditional language in a Given line does not fire (only Then lines are checked)."""
    art = _spec("""
        ## Acceptance

        - Given the user is authenticated if the token is valid
        - When the dashboard is requested
        - Then a 200 response is returned with the user's data
    """)
    assert PITFALL not in _ids(art)


def test_silent_modal_in_when_line_not_then():
    """Non-normative modal in a When line does not fire (only Then lines are checked)."""
    art = _spec("""
        ## Acceptance

        - Given the cache is warm
        - When the system may receive a high-traffic burst
        - Then a 200 response is returned within 200ms
    """)
    assert PITFALL not in _ids(art)


def test_silent_prose_ac_no_gherkin_mode():
    """Prose AC with no line-leading Gherkin keywords does not enter Gherkin mode."""
    art = _spec("""
        ## Acceptance

        The system should handle requests if the user is authenticated.
    """)
    assert PITFALL not in _ids(art)


def test_silent_plan_artifact_not_checked():
    """SPEC-MAQA-AC-CONDITIONAL does not apply to plan artifacts."""
    art = _plan("""
        ## Notes

        - Given deployment is triggered
        - When health checks pass
        - Then traffic should be routed to the new instances if readiness probes succeed
    """)
    assert PITFALL not in _ids(art)


def test_silent_fenced_then_line_ignored():
    """Then lines inside fenced code blocks are not scanned."""
    art = _spec("""
        ## Acceptance

        - Given the user logs in
        - When valid credentials are submitted
        - Then a JWT token is returned

        ```gherkin
        Then the system should emit an event if the flag is set
        ```
    """)
    assert PITFALL not in _ids(art)
