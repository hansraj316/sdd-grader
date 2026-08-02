"""Tests for the SPEC-MISSING-OUT-OF-SCOPE pitfall (spec with no Out-of-Scope/Non-Goals section)."""
from __future__ import annotations

import textwrap

from sddgrade.adapters.base import parse_sections
from sddgrade.catalog import load_catalog
from sddgrade.engine.lint import _spec_missing_out_of_scope
from sddgrade.model import Artifact, ArtifactType

CATALOG = load_catalog()
PITFALL = "SPEC-MISSING-OUT-OF-SCOPE"


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
    return [f.pitfall_id for f in _spec_missing_out_of_scope(art, CATALOG)]


# ── fires cases ───────────────────────────────────────────────────────────────

def test_fires_when_no_out_of_scope_heading():
    """Spec with 3+ normative reqs and no out-of-scope heading fires."""
    art = _spec("""
        ## Requirements

        FR-001: The system shall authenticate users via OAuth 2.0.
        FR-002: The system shall store session tokens in HttpOnly cookies.
        FR-003: The system shall expire sessions after 30 minutes of inactivity.
    """)
    assert PITFALL in _ids(art)


def test_fires_with_shall_lines_no_boundary():
    """Spec using shall-modals but no non-goals section fires."""
    art = _spec("""
        ## Functional Requirements

        The system shall validate the JWT signature before granting access.
        Users shall be redirected to login when their session expires.
        The API shall return 401 for unauthenticated requests.
    """)
    assert PITFALL in _ids(art)


def test_fires_with_fr_ids_no_boundary():
    """Spec using FR- IDs but no out-of-scope section fires."""
    art = _spec("""
        ## Requirements

        FR-001: Users can log in.
        FR-002: Users can reset their password.
        FR-003: Admins can manage user accounts.
    """)
    assert PITFALL in _ids(art)


def test_fires_with_mixed_normative_lines():
    """Spec mixing shall and FR- IDs (≥3 total) with no exclusion section fires."""
    art = _spec("""
        ## Requirements

        FR-001: The system shall allow CSV export.
        The data must be sanitised before export.
        NFR-001: Export shall complete within 5 seconds.

        ## Overview

        This feature adds data export to the dashboard.
    """)
    assert PITFALL in _ids(art)


def test_fires_finding_message_contains_pitfall_id():
    """Finding message includes SPEC-MISSING-OUT-OF-SCOPE."""
    art = _spec("""
        ## Requirements

        FR-001: The system shall do X.
        FR-002: The system shall do Y.
        FR-003: The system shall do Z.
    """)
    findings = _spec_missing_out_of_scope(art, CATALOG)
    assert findings
    assert "SPEC-MISSING-OUT-OF-SCOPE" in findings[0].message


# ── no-fire cases: heading variants ──────────────────────────────────────────

def test_no_fire_out_of_scope_heading():
    """Spec with '## Out of Scope' heading does not fire."""
    art = _spec("""
        ## Requirements

        FR-001: The system shall authenticate users via OAuth 2.0.
        FR-002: The system shall store session tokens in HttpOnly cookies.
        FR-003: The system shall expire sessions after 30 minutes of inactivity.

        ## Out of Scope

        This feature does not cover multi-factor authentication.
    """)
    assert PITFALL not in _ids(art)


def test_no_fire_non_goals_heading():
    """Spec with '## Non-Goals' heading does not fire."""
    art = _spec("""
        ## Requirements

        FR-001: The system shall authenticate users via OAuth 2.0.
        FR-002: The system shall store session tokens in HttpOnly cookies.
        FR-003: The system shall expire sessions after 30 minutes of inactivity.

        ## Non-Goals

        Real-time sync is out of scope for this release.
    """)
    assert PITFALL not in _ids(art)


def test_no_fire_nongoal_singular_heading():
    """Spec with '## Non-Goal' (singular) heading does not fire."""
    art = _spec("""
        ## Requirements

        FR-001: The system shall authenticate users via OAuth 2.0.
        FR-002: The system shall store session tokens in HttpOnly cookies.
        FR-003: The system shall expire sessions after 30 minutes of inactivity.

        ## Non-Goal

        Offline mode will not be implemented.
    """)
    assert PITFALL not in _ids(art)


def test_no_fire_not_in_scope_heading():
    """Spec with '## Not in Scope' heading does not fire."""
    art = _spec("""
        ## Requirements

        FR-001: The system shall authenticate users via OAuth 2.0.
        FR-002: The system shall store session tokens in HttpOnly cookies.
        FR-003: The system shall expire sessions after 30 minutes of inactivity.

        ## Not in Scope

        Admin bulk-import is not part of this feature.
    """)
    assert PITFALL not in _ids(art)


def test_no_fire_exclusions_heading():
    """Spec with '## Exclusions' heading does not fire."""
    art = _spec("""
        ## Requirements

        FR-001: The system shall authenticate users via OAuth 2.0.
        FR-002: The system shall store session tokens in HttpOnly cookies.
        FR-003: The system shall expire sessions after 30 minutes of inactivity.

        ## Exclusions

        Third-party integrations are excluded from v1.
    """)
    assert PITFALL not in _ids(art)


def test_no_fire_scope_boundaries_heading():
    """Spec with '## Scope Boundaries' heading does not fire."""
    art = _spec("""
        ## Requirements

        FR-001: The system shall authenticate users via OAuth 2.0.
        FR-002: The system shall store session tokens in HttpOnly cookies.
        FR-003: The system shall expire sessions after 30 minutes of inactivity.

        ## Scope Boundaries

        This feature covers only the web application, not the mobile client.
    """)
    assert PITFALL not in _ids(art)


# ── no-fire cases: insufficient normative content ─────────────────────────────

def test_no_fire_fewer_than_3_normative_lines():
    """Spec with only 2 normative lines does not fire (too thin to require a boundary section)."""
    art = _spec("""
        ## Requirements

        FR-001: The system shall do X.
        FR-002: The system shall do Y.

        ## Overview

        Thin spec.
    """)
    assert PITFALL not in _ids(art)


def test_no_fire_exactly_2_normative_lines():
    """Exactly 2 normative lines — below threshold — does not fire."""
    art = _spec("""
        ## Requirements

        The system shall authenticate users.
        The system shall log access attempts.
    """)
    assert PITFALL not in _ids(art)


def test_no_fire_zero_normative_lines():
    """Spec with no normative indicators does not fire."""
    art = _spec("""
        ## Overview

        This is a description of the feature. No formal requirements yet.
    """)
    assert PITFALL not in _ids(art)


# ── no-fire cases: non-spec artifact ─────────────────────────────────────────

def test_no_fire_plan_artifact():
    """Does not fire on plan.md even with no out-of-scope heading."""
    art = _plan("""
        ## Requirements

        FR-001: The deploy shall use blue-green.
        FR-002: The deploy must have a health check.
        FR-003: The deploy shall support rollback.
    """)
    assert PITFALL not in _ids(art)
