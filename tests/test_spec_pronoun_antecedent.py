"""Tests for SPEC-PRONOUN-ANTECEDENT — ambiguous object pronouns in requirements."""
from __future__ import annotations

import textwrap

from sddgrade.adapters.base import parse_sections
from sddgrade.catalog import load_catalog
from sddgrade.engine.lint import _pronoun_antecedent
from sddgrade.model import Artifact, ArtifactType

CATALOG = load_catalog()
PITFALL = "SPEC-PRONOUN-ANTECEDENT"


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
    return [f.pitfall_id for f in _pronoun_antecedent(art, CATALOG)]


# ------------------------------------------------------------------ fires cases

def test_fires_on_it_after_shall_in_fr_line():
    """FR-labelled line using 'it' after 'shall' triggers SPEC-PRONOUN-ANTECEDENT."""
    art = _spec("""
        ## Requirements

        - FR-001: The system shall send it to the client via the API.
    """)
    assert PITFALL in _ids(art)


def test_fires_on_them_after_shall():
    """'them' after 'shall' on a requirement line triggers the check."""
    art = _spec("""
        ## Requirements

        - FR-002: The service shall deliver them within 24 hours.
    """)
    assert PITFALL in _ids(art)


def test_fires_on_their_after_must():
    """'their' after 'must' on a requirement line triggers the check."""
    art = _spec("""
        ## Requirements

        - FR-003: The gateway must validate their tokens before granting access.
    """)
    assert PITFALL in _ids(art)


def test_fires_on_this_after_shall():
    """'this' after 'shall' on a requirement line triggers the check."""
    art = _spec("""
        ## Requirements

        - FR-004: The system shall store this in the database.
    """)
    assert PITFALL in _ids(art)


def test_fires_on_that_after_must():
    """'that' after 'must' on a requirement line triggers the check."""
    art = _spec("""
        ## Requirements

        - NFR-001: The service must not expose that to external callers.
    """)
    assert PITFALL in _ids(art)


def test_fires_on_these_after_shall():
    """'these' after 'shall' on a requirement line triggers the check."""
    art = _spec("""
        ## Requirements

        - FR-005: The API shall return these in JSON format.
    """)
    assert PITFALL in _ids(art)


def test_fires_on_those_after_must():
    """'those' after 'must' on a requirement line triggers the check."""
    art = _spec("""
        ## Requirements

        - FR-006: The system must archive those after 90 days.
    """)
    assert PITFALL in _ids(art)


def test_silent_on_possessive_its():
    """Possessive 'its' is excluded — it modifies a noun and its antecedent is typically clear."""
    art = _spec("""
        ## Requirements

        - FR-007: The module shall expose its state via the status endpoint.
    """)
    assert _ids(art) == []


def test_fires_on_multiple_lines_reports_count():
    """Multiple pronoun-bearing lines produce a single finding with correct count."""
    art = _spec("""
        ## Requirements

        - FR-010: The system shall send it to the consumer.
        - FR-011: The service must forward them to the queue.
    """)
    findings = _pronoun_antecedent(art, CATALOG)
    assert len(findings) == 1
    assert "2" in findings[0].message


# ------------------------------------------------------------------ silent cases

def test_silent_on_clear_noun_object():
    """No pronoun after modal — no finding."""
    art = _spec("""
        ## Requirements

        - FR-020: The system shall send the access token to the requesting client.
    """)
    assert _ids(art) == []


def test_silent_on_subject_pronoun_only():
    """Subject pronoun ('it shall') is SPEC-UNCLEAR-ACTOR's domain — this check is silent."""
    art = _spec("""
        ## Requirements

        - FR-021: It shall process the request within 200ms.
    """)
    assert _ids(art) == []


def test_silent_on_non_requirement_prose():
    """Pronoun after modal in non-requirement prose section is not flagged."""
    art = _spec("""
        ## Overview

        The system shall send it when triggered — but this is prose background, not a requirement.
    """)
    assert _ids(art) == []


def test_silent_on_plan_artifact():
    """Check does not apply to plan.md artifacts."""
    art = _plan("""
        ## Deployment Steps

        - FR-001: The service shall route it to the correct shard.
    """)
    assert _ids(art) == []


def test_silent_when_pronoun_in_fenced_block():
    """Pronouns inside fenced code blocks are not flagged."""
    art = _spec("""
        ## Requirements

        - FR-030: The system shall validate inputs.

        ```python
        # it shall handle this
        def validate(it):
            return it is not None
        ```
    """)
    assert _ids(art) == []


def test_finding_line_number_points_to_first_hit():
    """Finding line number corresponds to the first matching requirement line."""
    art = _spec("""
        ## Requirements

        - FR-040: The system shall resolve it to the canonical URL.
    """)
    findings = _pronoun_antecedent(art, CATALOG)
    assert len(findings) == 1
    assert findings[0].line == 3
