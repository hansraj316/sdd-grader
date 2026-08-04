"""Tests for SPEC-AC-VAGUE-OUTCOME pitfall (vague Then clause in formal Gherkin ACs)."""
from __future__ import annotations

import textwrap

from sddgrade.adapters.base import parse_sections
from sddgrade.catalog import load_catalog
from sddgrade.engine.lint import _spec_ac_vague_outcome
from sddgrade.model import Artifact, ArtifactType

CATALOG = load_catalog()
PITFALL = "SPEC-AC-VAGUE-OUTCOME"


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
    return [f.pitfall_id for f in _spec_ac_vague_outcome(art, CATALOG)]


# ── fire cases ────────────────────────────────────────────────────────────────

def test_fires_correctly_in_then_clause():
    """Then clause with 'correctly' fires."""
    art = _spec("""
        ## Acceptance

        - Given the user submits a form
        - When the data is valid
        - Then the system correctly processes the request
    """)
    assert PITFALL in _ids(art)


def test_fires_properly_in_then_clause():
    """Then clause with 'properly' fires."""
    art = _spec("""
        ## Acceptance

        - Given an API call is made
        - When the payload is well-formed
        - Then the response is properly returned
    """)
    assert PITFALL in _ids(art)


def test_fires_appropriately_in_then_clause():
    """Then clause with 'appropriately' fires."""
    art = _spec("""
        ## Acceptance

        - Given an error occurs
        - When the system detects the failure
        - Then the user is appropriately notified
    """)
    assert PITFALL in _ids(art)


def test_fires_as_expected_in_then_clause():
    """Then clause with 'as expected' fires."""
    art = _spec("""
        ## Acceptance

        - Given valid credentials are entered
        - When the login form is submitted
        - Then the system behaves as expected
    """)
    assert PITFALL in _ids(art)


def test_fires_as_intended_in_then_clause():
    """Then clause with 'as intended' fires."""
    art = _spec("""
        ## Acceptance

        - Given the feature flag is enabled
        - When a request arrives
        - Then the new flow executes as intended
    """)
    assert PITFALL in _ids(art)


def test_fires_multiple_vague_then_clauses_reports_first():
    """Multiple vague Then clauses report a single finding anchored at first."""
    art = _spec("""
        ## Acceptance

        - Given a user logs in
        - When valid credentials are provided
        - Then the session is correctly established

        - Given a user logs out
        - When the logout action is triggered
        - Then the session is properly terminated
    """)
    findings = _spec_ac_vague_outcome(art, CATALOG)
    assert len(findings) == 1
    assert PITFALL in findings[0].pitfall_id


# ── silent cases ──────────────────────────────────────────────────────────────

def test_silent_concrete_then_clause():
    """Then clause with observable outcome does not fire."""
    art = _spec("""
        ## Acceptance

        - Given the user submits a form
        - When the data is valid
        - Then a 201 response is returned and the record is saved to the database
    """)
    assert PITFALL not in _ids(art)


def test_silent_no_gherkin_line_leaders():
    """Prose AC without line-leading Given/When/Then does not enter Gherkin mode."""
    art = _spec("""
        ## Acceptance

        The system should correctly handle all requests.
    """)
    assert PITFALL not in _ids(art)


def test_silent_missing_when_leader():
    """Spec with Given but no When line-leader does not enter Gherkin mode."""
    art = _spec("""
        ## Acceptance

        - Given the user is authenticated
        - Then the system correctly processes the request
    """)
    assert PITFALL not in _ids(art)


def test_silent_missing_given_leader():
    """Spec with When but no Given line-leader does not enter Gherkin mode."""
    art = _spec("""
        ## Acceptance

        - When the user clicks submit
        - Then the form is correctly validated
    """)
    assert PITFALL not in _ids(art)


def test_silent_single_line_gherkin_style():
    """Single-line 'Given … when … then …' does not enter Gherkin mode (When is not line-leading)."""
    art = _spec("""
        ## Acceptance

        - Given I have tasks, when I export, then the CSV is correctly formatted.
    """)
    assert PITFALL not in _ids(art)


def test_silent_vague_word_not_in_then_line():
    """Vague word in a Given or When line does not fire."""
    art = _spec("""
        ## Acceptance

        - Given the system correctly detects the issue
        - When the event is processed
        - Then an alert is sent to /api/alerts
    """)
    assert PITFALL not in _ids(art)


def test_silent_plan_artifact_not_checked():
    """SPEC-AC-VAGUE-OUTCOME does not apply to plan artifacts."""
    art = _plan("""
        ## Deployment

        - Given deployment is triggered
        - When health checks pass
        - Then traffic is correctly routed to the new instances
    """)
    assert PITFALL not in _ids(art)


def test_silent_inline_correctly_in_non_then_context():
    """'Correctly' appearing only in prose (no Gherkin mode) does not fire."""
    art = _spec("""
        ## Requirements

        - FR-001: The system shall correctly validate all inputs.
    """)
    assert PITFALL not in _ids(art)
