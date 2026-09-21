"""Tests for SPEC-US-NO-AC pitfall.

Fires when a spec.md has ≥1 US-NNN section heading whose span (from the heading
to the next sibling/ancestor heading) contains no AC-NNN acceptance-criteria line.

Sources: Spec-Kit template, INVEST ('Testable'), ISO/IEC/IEEE 29148:2018 §5.2.3.
"""
from __future__ import annotations

import textwrap

from sddgrade.adapters.base import parse_sections
from sddgrade.catalog import load_catalog
from sddgrade.engine.lint import _spec_us_no_ac
from sddgrade.model import Artifact, ArtifactType

CATALOG = load_catalog()
PITFALL = "SPEC-US-NO-AC"


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
    return [f.pitfall_id for f in _spec_us_no_ac(art, CATALOG)]


# ---------------------------------------------------------------------------
# Silent cases
# ---------------------------------------------------------------------------


def test_silent_no_us_headings():
    """Spec with no US-NNN headings — guard does not fire."""
    art = _spec("""
        # Feature Spec
        ## Requirements
        FR-001: The system shall allow login.
        AC-001: Given a valid user, when they submit credentials, then they are logged in.
    """)
    assert PITFALL not in _ids(art)


def test_silent_us_section_with_ac():
    """US-NNN section that contains AC-NNN line — no finding."""
    art = _spec("""
        # Login Feature
        ## US-001: User Login
        As a registered user I want to log in.
        AC-001: Given valid credentials, when I submit, then I am authenticated.
    """)
    assert PITFALL not in _ids(art)


def test_silent_us_section_ac_in_subsection():
    """AC-NNN in a sub-heading below the US-NNN section is still in its span."""
    art = _spec("""
        # Feature
        ## US-001: Checkout
        As a shopper I want to complete my purchase.
        ### Acceptance Criteria
        AC-001: Given items in cart, when I pay, then the order is created.
    """)
    assert PITFALL not in _ids(art)


def test_silent_multiple_us_sections_all_have_ac():
    """All US-NNN sections have at least one AC — no finding."""
    art = _spec("""
        # Feature
        ## US-001: Login
        AC-001: Given valid creds, when submitted, then authenticated.
        ## US-002: Logout
        AC-002: Given logged-in user, when they click logout, then session is cleared.
    """)
    assert PITFALL not in _ids(art)


def test_silent_non_spec_artifact():
    """Check does not apply to plan.md."""
    art = _plan("""
        # Deployment Plan
        ## US-001: Deploy Login
        No AC here.
    """)
    assert PITFALL not in _ids(art)


def test_silent_ac_in_fenced_code_not_counted():
    """AC-NNN inside a fenced code block does NOT silence the check."""
    art = _spec("""
        # Feature
        ## US-001: Payment
        As a buyer I want to pay.
        ```
        AC-001: this is inside a code fence
        ```
    """)
    assert PITFALL in _ids(art)


# ---------------------------------------------------------------------------
# Firing cases
# ---------------------------------------------------------------------------


def test_fires_us_section_no_ac():
    """US-NNN section with zero AC-NNN lines fires the check."""
    art = _spec("""
        # Feature
        ## US-001: User Registration
        As a new user I want to register an account so that I can use the service.
        FR-001: The system shall accept email and password during registration.
    """)
    assert PITFALL in _ids(art)


def test_fires_one_missing_one_present():
    """Two US-NNN sections — one has AC, one does not — check fires once."""
    art = _spec("""
        # Feature
        ## US-001: Login
        AC-001: Given valid credentials, when submitted, then authenticated.
        ## US-002: Password Reset
        As a user I want to reset my password.
        FR-002: The system shall send a reset email.
    """)
    findings = _spec_us_no_ac(art, CATALOG)
    assert any(f.pitfall_id == PITFALL for f in findings)
    # Only US-002 is flagged.
    msgs = [f.message for f in findings if f.pitfall_id == PITFALL]
    assert len(msgs) == 1
    assert "US-002" in msgs[0]


def test_fires_multiple_missing_aggregate():
    """Multiple US-NNN sections without AC produce a single aggregate finding."""
    art = _spec("""
        # Feature
        ## US-001: Login
        FR-001: The system shall authenticate users.
        ## US-002: Logout
        FR-002: The system shall invalidate the session.
        ## US-003: Profile
        FR-003: The system shall display user profile.
    """)
    findings = _spec_us_no_ac(art, CATALOG)
    pitfall_findings = [f for f in findings if f.pitfall_id == PITFALL]
    assert len(pitfall_findings) == 1
    msg = pitfall_findings[0].message
    assert "3 user stories" in msg or "US-001" in msg


def test_fires_us_section_empty_body():
    """US-NNN section with completely empty body fires the check."""
    art = _spec("""
        # Feature
        ## US-001: Login

        ## US-002: Logout
        AC-002: Given session, when logout clicked, then session cleared.
    """)
    findings = _spec_us_no_ac(art, CATALOG)
    assert any(f.pitfall_id == PITFALL for f in findings)
    msgs = [f.message for f in findings if f.pitfall_id == PITFALL]
    assert "US-001" in msgs[0]


def test_silent_ac_anywhere_in_span():
    """AC-NNN anywhere in the US section span silences the check for that story."""
    art = _spec("""
        # Feature
        ## US-001: Search
        As a user I want to search content.
        FR-001: The system shall return results within 500 ms.
        Some more prose.
        AC-001: Given a search query, when submitted, then results appear within 500 ms.
    """)
    assert PITFALL not in _ids(art)
