"""Tests for REQ-WEAK-DIRECTIVE — requirement lines using non-normative modal verbs."""
from __future__ import annotations

import textwrap

from sddgrade.adapters.base import parse_sections
from sddgrade.catalog import load_catalog
from sddgrade.engine.lint import _weak_directive
from sddgrade.model import Artifact, ArtifactType

CATALOG = load_catalog()
PITFALL = "REQ-WEAK-DIRECTIVE"


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
    return [f.pitfall_id for f in _weak_directive(art, CATALOG)]


# ------------------------------------------------------------------ fires cases

def test_fires_on_should_in_fr_line():
    """FR-labelled line using 'should' triggers REQ-WEAK-DIRECTIVE."""
    art = _spec("""
        ## Requirements

        - FR-001: The system should encrypt all tokens at rest.
    """)
    assert PITFALL in _ids(art)


def test_fires_on_may_in_nfr_line():
    """NFR-labelled line using 'may' triggers REQ-WEAK-DIRECTIVE."""
    art = _spec("""
        ## Non-Functional Requirements

        - NFR-003: The service may respond within 500ms under peak load.
    """)
    assert PITFALL in _ids(art)


def test_fires_on_could_in_requirements_section():
    """'could' in a Requirements section line triggers the check."""
    art = _spec("""
        ## Requirements

        The API could support OAuth 2.0 token refresh.
    """)
    assert PITFALL in _ids(art)


def test_fires_on_might_in_acceptance_section():
    """'might' in an Acceptance section line triggers the check."""
    art = _spec("""
        ## Acceptance Criteria

        The upload process might handle files up to 10MB.
    """)
    assert PITFALL in _ids(art)


def test_fires_multiple_occurrences_reported():
    """Multiple weak-directive lines are counted together."""
    art = _spec("""
        ## Requirements

        - FR-001: The system should log all errors.
        - FR-002: The API may return a 429 on rate limit.
        - FR-003: The cache could expire entries after 1 hour.
    """)
    findings = _weak_directive(art, CATALOG)
    assert any(f.pitfall_id == PITFALL for f in findings)
    msg = next(f.message for f in findings if f.pitfall_id == PITFALL)
    assert "3" in msg


def test_message_names_modal_verb():
    """Finding message includes the offending modal verb."""
    art = _spec("""
        ## Requirements

        - FR-010: The system should validate input before processing.
    """)
    findings = _weak_directive(art, CATALOG)
    assert any(f.pitfall_id == PITFALL for f in findings)
    msg = next(f.message for f in findings if f.pitfall_id == PITFALL)
    assert "should" in msg


# ------------------------------------------------------------------ silent cases

def test_silent_when_shall_used():
    """'shall' on requirement lines does not trigger the check."""
    art = _spec("""
        ## Requirements

        - FR-001: The system shall encrypt all tokens at rest.
        - FR-002: The API shall return 429 on rate limit.
    """)
    assert PITFALL not in _ids(art)


def test_silent_when_must_used():
    """'must' on requirement lines does not trigger the check."""
    art = _spec("""
        ## Requirements

        - NFR-001: Response time must not exceed 200ms at p99.
    """)
    assert PITFALL not in _ids(art)


def test_silent_when_shall_and_should_same_line():
    """Line with both 'shall' and 'should' is treated as a legitimate conditional."""
    art = _spec("""
        ## Requirements

        - FR-001: When retrying, the system shall attempt at most 3 times and should wait 1s between attempts.
    """)
    assert PITFALL not in _ids(art)


def test_silent_on_prose_outside_requirements_section():
    """'should' in a prose heading or overview section is not flagged."""
    art = _spec("""
        # Overview

        This feature should be considered carefully. The design should evolve.

        ## Background

        Developers should review this document before implementation.
    """)
    assert PITFALL not in _ids(art)


def test_silent_on_plan_artifact():
    """REQ-WEAK-DIRECTIVE only applies to spec.md, not plan.md."""
    art = _plan("""
        ## Steps

        - The team should deploy to staging first.
        - May need additional review from security team.
    """)
    assert PITFALL not in _ids(art)


def test_silent_on_fenced_code_block():
    """'should' inside a fenced code block is not flagged."""
    art = _spec("""
        ## Requirements

        - FR-001: The system shall validate the config.

        ```
        # Example — note: should use strict mode
        validate(config, strict=True)
        ```
    """)
    assert PITFALL not in _ids(art)


def test_fires_on_scenario_section():
    """Weak directive in a Scenario section is flagged."""
    art = _spec("""
        ## Acceptance Scenarios

        When the user logs in, the token may be refreshed automatically.
    """)
    assert PITFALL in _ids(art)


def test_fires_once_per_artifact():
    """Multiple weak-directive lines produce exactly one finding."""
    art = _spec("""
        ## Requirements

        - FR-001: The system should encrypt tokens.
        - FR-002: The API may cache responses.
        - FR-003: The client could retry on 503.
    """)
    findings = [f for f in _weak_directive(art, CATALOG) if f.pitfall_id == PITFALL]
    assert len(findings) == 1
