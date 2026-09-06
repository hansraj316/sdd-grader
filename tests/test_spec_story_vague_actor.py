"""Tests for SPEC-STORY-VAGUE-ACTOR pitfall.

A user story with the generic actor 'a user' or 'an end user' instead of a
specific role fires this check. Qualified actors like 'As a logged-in user'
or 'As an admin user' are SILENT because the qualifier precedes "user".

Source: INVEST Negotiable criterion + ISO/IEC/IEEE 29148:2018 §5.2.1
"""
from __future__ import annotations

import textwrap

from sddgrade.adapters.base import parse_sections
from sddgrade.catalog import load_catalog
from sddgrade.engine.lint import _spec_story_vague_actor
from sddgrade.model import Artifact, ArtifactType

CATALOG = load_catalog()
PITFALL = "SPEC-STORY-VAGUE-ACTOR"


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
    return [f.pitfall_id for f in _spec_story_vague_actor(art, CATALOG)]


# ── fires cases ───────────────────────────────────────────────────────────────

def test_fires_bare_user_actor():
    """'As a user, I want to' → fires (bare generic actor)."""
    art = _spec("""
        ## User Story US-001

        As a user, I want to log in so that I can access my account.

        ## Requirements
        - FR-001: The system shall authenticate users.
        - FR-002: The system shall log failed attempts.
        - FR-003: The system shall support SSO.
    """)
    assert PITFALL in _ids(art)


def test_fires_end_user_actor():
    """'As an end user, I want to' → fires (generic 'end user')."""
    art = _spec("""
        ## User Story

        As an end user, I want to export my data so that I can analyse it offline.

        ## Requirements
        - FR-001: The system shall export data.
    """)
    assert PITFALL in _ids(art)


def test_fires_end_user_hyphenated():
    """'As an end-user, I want to' → fires (hyphenated variant)."""
    art = _spec("""
        ## User Story

        As an end-user, I want to view reports so that I can track progress.

        ## Requirements
        - FR-001: The system shall generate reports.
    """)
    assert PITFALL in _ids(art)


def test_fires_multiple_vague_actors():
    """Two vague-actor stories → fires (aggregate finding, count=2)."""
    art = _spec("""
        ## User Stories

        As a user, I want to log in so that I can access my account.
        As a user, I want to reset my password so that I can regain access.

        ## Requirements
        - FR-001: The system shall authenticate users.
    """)
    findings = _spec_story_vague_actor(art, CATALOG)
    assert any(f.pitfall_id == PITFALL for f in findings)
    # message should mention count of violations
    msg = findings[0].message if findings else ""
    assert "2" in msg


def test_fires_list_marker_prefix():
    """'- As a user, I want' (list-marker prefix) → fires."""
    art = _spec("""
        ## User Stories

        - As a user, I want to search so that I can find content quickly.

        ## Requirements
        - FR-001: The system shall return results within 200ms.
    """)
    assert PITFALL in _ids(art)


# ── silent cases ──────────────────────────────────────────────────────────────

def test_silent_specific_role():
    """'As an admin, I want to' → silent (specific named role)."""
    art = _spec("""
        ## User Story US-001

        As an admin, I want to manage user accounts so that I can onboard staff.

        ## Requirements
        - FR-001: The system shall allow admins to create users.
    """)
    assert PITFALL not in _ids(art)


def test_silent_qualified_user_loggedin():
    """'As a logged-in user, I want to' → silent (qualifier before 'user')."""
    art = _spec("""
        ## User Story US-001

        As a logged-in user, I want to view my profile so that I can update it.

        ## Requirements
        - FR-001: The system shall display the profile page.
    """)
    assert PITFALL not in _ids(art)


def test_silent_qualified_user_new():
    """'As a new user, I want to' → silent (qualifier 'new' before 'user')."""
    art = _spec("""
        ## User Story US-001

        As a new user, I want to complete onboarding so that I can use the app.

        ## Requirements
        - FR-001: The system shall present an onboarding wizard.
    """)
    assert PITFALL not in _ids(art)


def test_silent_qualified_user_admin():
    """'As an admin user, I want to' → silent (qualifier 'admin' before 'user')."""
    art = _spec("""
        ## User Story US-001

        As an admin user, I want to export logs so that I can audit activity.

        ## Requirements
        - FR-001: The system shall export audit logs.
    """)
    assert PITFALL not in _ids(art)


def test_silent_no_story_format():
    """Spec with no Connextra story opener → silent (guard)."""
    art = _spec("""
        ## Requirements

        FR-001: The system shall authenticate users via SSO.
        FR-002: The system shall log failed login attempts.
        FR-003: The system shall support MFA.
    """)
    assert PITFALL not in _ids(art)


def test_silent_plan_artifact():
    """Plan artifact → silent (check only applies to spec)."""
    art = _plan("""
        ## Deployment

        As a user, I want to deploy to production.

        ## Steps
        - Deploy the service.
        - Run migrations.
        - Verify health checks.
    """)
    assert PITFALL not in _ids(art)


def test_silent_user_without_i_want():
    """'As a user' but no 'I want' on the line → silent (guard requires I-want)."""
    art = _spec("""
        ## Background

        As a user, the system should present a dashboard.

        ## Requirements
        - FR-001: The system shall authenticate users.
        - FR-002: The system shall show a dashboard.
        - FR-003: The system shall log activity.
    """)
    # No 'I want' → _I_WANT_RE fails → no finding from this function
    assert PITFALL not in _ids(art)


def test_silent_specific_multiword_role():
    """'As a payroll manager, I want to' → silent (two-word specific role)."""
    art = _spec("""
        ## User Story US-001

        As a payroll manager, I want to export reports so that I can audit salaries.

        ## Requirements
        - FR-001: The system shall generate payroll exports.
    """)
    assert PITFALL not in _ids(art)
