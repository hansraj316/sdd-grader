"""Tests for SPEC-STORY-NO-BENEFIT — user stories missing the 'so that [benefit]' clause."""
from __future__ import annotations

import textwrap

from sddgrade.adapters.base import parse_sections
from sddgrade.catalog import load_catalog
from sddgrade.engine.lint import _story_no_benefit
from sddgrade.model import Artifact, ArtifactType


def _spec(raw: str) -> Artifact:
    raw = textwrap.dedent(raw).strip()
    return Artifact(
        path="spec.md",
        type=ArtifactType.SPEC,
        feature_id="test",
        raw=raw,
        sections=parse_sections(raw),
    )


CATALOG = load_catalog()
PITFALL = "SPEC-STORY-NO-BENEFIT"


def _ids(art: Artifact) -> list[str]:
    return [f.pitfall_id for f in _story_no_benefit(art, CATALOG)]


# ---- fires when "so that" is absent -----------------------------------------

def test_fires_on_story_without_so_that():
    art = _spec("## User Story\nAs a user, I want to log in.")
    assert PITFALL in _ids(art)


def test_fires_on_an_prefix_story():
    art = _spec("## User Story\nAs an analyst, I want to view reports.")
    assert PITFALL in _ids(art)


def test_fires_on_bullet_prefixed_story():
    art = _spec("## User Story\n- As a user, I want notifications.")
    assert PITFALL in _ids(art)


def test_fires_when_some_stories_missing_benefit():
    art = _spec(
        "## User Story\n"
        "As a user, I want to log in, so that I can access my account.\n"
        "As an admin, I want to reset passwords.\n"
    )
    assert PITFALL in _ids(art)


# ---- silent when "so that" is present ---------------------------------------

def test_silent_when_so_that_on_same_line():
    art = _spec(
        "## User Story\nAs a user, I want to log in, so that I can access my account."
    )
    assert PITFALL not in _ids(art)


def test_silent_when_so_that_on_next_line():
    art = _spec(
        "## User Story\n"
        "As a user, I want to log in,\n"
        "so that I can access my account."
    )
    assert PITFALL not in _ids(art)


def test_silent_when_so_that_after_blank_line():
    art = _spec(
        "## User Story\n"
        "As a user, I want to log in,\n\n"
        "so that I can access my account."
    )
    assert PITFALL not in _ids(art)


def test_silent_when_all_stories_have_benefit():
    art = _spec(
        "## User Story\n"
        "As a user, I want to log in, so that I can access my account.\n"
        "As an admin, I want to reset passwords, so that users are not locked out.\n"
    )
    assert PITFALL not in _ids(art)


def test_silent_on_bullet_prefixed_story_with_benefit():
    art = _spec(
        "## User Story\n- As a user, I want notifications, so that I stay informed."
    )
    assert PITFALL not in _ids(art)


# ---- guard: skip specs with no user stories ---------------------------------

def test_silent_on_spec_with_no_user_stories():
    art = _spec(
        "## Functional Requirements\n"
        "FR-001: The system shall export CSV.\n"
    )
    assert PITFALL not in _ids(art)
