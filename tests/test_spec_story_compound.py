"""Tests for the SPEC-STORY-COMPOUND pitfall (compound user-story header — INVEST Small violation)."""
from __future__ import annotations

import textwrap

from sddgrade.adapters.base import parse_sections
from sddgrade.catalog import load_catalog
from sddgrade.engine.lint import _spec_story_compound
from sddgrade.model import Artifact, ArtifactType

CATALOG = load_catalog()
PITFALL = "SPEC-STORY-COMPOUND"


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
    return [f.pitfall_id for f in _spec_story_compound(art, CATALOG)]


# ── fires cases ───────────────────────────────────────────────────────────────

def test_fires_two_wants_with_and():
    """As a user, I want to X and Y → fires (2 capabilities)."""
    art = _spec("""
        ## User Story

        As a user, I want to log in and reset my password.
    """)
    assert PITFALL in _ids(art)


def test_fires_three_wants_with_two_ands():
    """As a user, I want to X and Y and Z → fires (3 capabilities)."""
    art = _spec("""
        ## User Story

        As a user, I want to log in and reset my password and view my profile.
    """)
    assert PITFALL in _ids(art)


def test_fires_compound_want_before_so_that():
    """Compound want before 'so that' benefit clause still fires."""
    art = _spec("""
        ## User Story

        As an admin, I want to create and delete user accounts so that I can manage access.
    """)
    assert PITFALL in _ids(art)


def test_fires_as_an_variant():
    """'As an X' opener (not 'As a') also fires."""
    art = _spec("""
        ## User Story

        As an operator, I want to start and stop services.
    """)
    assert PITFALL in _ids(art)


def test_fires_multiple_compound_stories_reports_first_line():
    """Multiple compound stories: finding anchored at the first offending line."""
    art = _spec("""
        ## User Story

        As a user, I want to search and filter results.

        As an admin, I want to create and archive projects.
    """)
    findings = _spec_story_compound(art, CATALOG)
    assert len(findings) == 1
    assert findings[0].pitfall_id == PITFALL
    # First compound story must be the anchor.
    assert findings[0].line is not None
    assert findings[0].line < 10


def test_fires_want_verb_phrase_with_and():
    """Verb phrase like 'search and filter' in the want clause fires."""
    art = _spec("""
        ## User Story

        As a customer, I want to browse and purchase items.
    """)
    assert PITFALL in _ids(art)


# ── silent cases ─────────────────────────────────────────────────────────────

def test_silent_single_want_no_and():
    """Single capability in want clause — no 'and' → silent."""
    art = _spec("""
        ## User Story

        As a user, I want to log in so that I can access my dashboard.
    """)
    assert PITFALL not in _ids(art)


def test_silent_and_only_in_benefit_clause():
    """'and' appears only in 'so that' benefit clause, not the want → silent."""
    art = _spec("""
        ## User Story

        As a user, I want to export my report so that I can share it with my manager and team.
    """)
    assert PITFALL not in _ids(art)


def test_silent_no_story_opener():
    """Spec with no Connextra opener at all → silent (guard fires)."""
    art = _spec("""
        ## Requirements

        FR-001: The system shall authenticate users.
        FR-002: The system shall log all login attempts.
    """)
    assert PITFALL not in _ids(art)


def test_silent_non_spec_artifact():
    """Plan artifact — pitfall only applies to spec → silent."""
    art = _plan("""
        ## Deployment

        As a user, I want to install and configure the tool.
    """)
    assert PITFALL not in _ids(art)


def test_silent_story_with_single_want_containing_no_and():
    """'want to configure the system' — no 'and' → silent."""
    art = _spec("""
        ## User Story

        As a developer, I want to configure the system via environment variables.
    """)
    assert PITFALL not in _ids(art)


def test_silent_and_in_prose_outside_story():
    """'and' appears in prose outside any story opener line → silent."""
    art = _spec("""
        ## Overview

        This feature handles authentication and authorisation.

        As a user, I want to log in so that I can access my account.
    """)
    assert PITFALL not in _ids(art)


def test_silent_want_adjective_no_to():
    """'I want fast and intuitive X' — no 'to' after want — adjectives, not compound wants → silent."""
    art = _spec("""
        ## User Story

        As a user, I want fast and intuitive search so that I can find things easily.
    """)
    assert PITFALL not in _ids(art)


def test_silent_story_with_and_in_so_that_only():
    """Want clause is single; benefit lists two outcomes with 'and' → silent."""
    art = _spec("""
        ## User Story

        As a user, I want to reset my password so that I regain access and stay secure.
    """)
    assert PITFALL not in _ids(art)


def test_fires_count_in_message():
    """Finding message reports compound story count."""
    art = _spec("""
        ## User Story

        As a user, I want to search and filter results.
        As a user, I want to download and share reports.
    """)
    findings = _spec_story_compound(art, CATALOG)
    assert findings
    assert "2" in findings[0].message
