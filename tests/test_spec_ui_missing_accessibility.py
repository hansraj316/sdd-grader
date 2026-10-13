"""Tests for SPEC-UI-MISSING-ACCESSIBILITY pitfall.

Guard: spec artifact + ≥3 non-fenced FR-/NFR- lines.
Trigger: any non-fenced non-heading line has UI vocabulary (React/Vue/Angular/SPA/browser/…).
Silence: any non-fenced line anywhere contains accessibility vocabulary (wcag/a11y/…).
Fires one aggregate finding at the first trigger line.

Source: Tessl frontend quality checklist, WCAG 2.1, Section 508, EN 301 549,
        ISO 9241-171:2008.
"""
from __future__ import annotations

import textwrap

from sddgrade.adapters.base import parse_sections
from sddgrade.catalog import load_catalog
from sddgrade.engine.lint import _spec_ui_missing_accessibility
from sddgrade.model import Artifact, ArtifactType

CATALOG = load_catalog()
PITFALL = "SPEC-UI-MISSING-ACCESSIBILITY"


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
    return [f.pitfall_id for f in _spec_ui_missing_accessibility(art, CATALOG)]


# ── FIRE cases ───────────────────────────────────────────────────────────────

def test_fire_react_no_a11y():
    """React in FR line, no accessibility vocab → fires."""
    art = _spec("""
        ## Requirements

        FR-001: The React frontend shall display a dashboard.
        FR-002: The system shall authenticate users via OAuth.
        FR-003: The system shall expose a REST API.
    """)
    assert PITFALL in _ids(art)


def test_fire_angular_no_a11y():
    """Angular keyword → fires."""
    art = _spec("""
        ## Requirements

        FR-001: The Angular web app shall render a report view.
        FR-002: The system shall store user data in PostgreSQL.
        NFR-001: The system shall respond within 200ms.
    """)
    assert PITFALL in _ids(art)


def test_fire_spa_no_a11y():
    """SPA keyword → fires."""
    art = _spec("""
        ## Requirements

        FR-001: The SPA shall support offline mode.
        FR-002: The system shall handle concurrent users.
        FR-003: The system shall log audit events.
    """)
    assert PITFALL in _ids(art)


def test_fire_frontend_no_a11y():
    """'frontend' keyword → fires."""
    art = _spec("""
        ## Requirements

        FR-001: The frontend shall display user notifications.
        FR-002: The system shall process payments.
        FR-003: The API shall enforce rate limits.
    """)
    assert PITFALL in _ids(art)


def test_fire_browser_client_no_a11y():
    """'browser' keyword in FR line → fires."""
    art = _spec("""
        ## Requirements

        FR-001: The browser client shall cache responses locally.
        FR-002: The system shall process uploads.
        FR-003: The system shall cache results.
    """)
    assert PITFALL in _ids(art)


def test_fire_vue_no_a11y():
    """Vue.js keyword → fires."""
    art = _spec("""
        ## Requirements

        FR-001: The Vue application shall render a product catalog.
        FR-002: The system shall support search.
        FR-003: The system shall integrate with Stripe.
    """)
    assert PITFALL in _ids(art)


# ── SILENT cases ──────────────────────────────────────────────────────────────

def test_silent_wcag_present():
    """React frontend + WCAG anywhere in spec → silent."""
    art = _spec("""
        ## Requirements

        FR-001: The React frontend shall display a dashboard.
        FR-002: The system shall authenticate users.
        FR-003: The system shall log events.
        NFR-A1: The application shall conform to WCAG 2.1 Level AA.
    """)
    assert PITFALL not in _ids(art)


def test_silent_a11y_present():
    """a11y keyword anywhere → silent."""
    art = _spec("""
        ## Requirements

        FR-001: The Angular SPA shall render charts.
        FR-002: The system shall store state.
        FR-003: The system shall send emails.
        NFR-A1: All components shall pass a11y audit.
    """)
    assert PITFALL not in _ids(art)


def test_silent_accessibility_word():
    """'accessibility' word anywhere → silent."""
    art = _spec("""
        ## Requirements

        FR-001: The Vue frontend shall display forms.
        FR-002: The system shall persist data.
        FR-003: The system shall handle payments.
        NFR-A1: The UI shall meet accessibility standards.
    """)
    assert PITFALL not in _ids(art)


def test_silent_screen_reader_present():
    """'screen reader' → silent."""
    art = _spec("""
        ## Requirements

        FR-001: The browser client shall render tables.
        FR-002: The system shall process uploads.
        FR-003: The system shall cache results.
        NFR-A1: The application shall be operable with screen reader software.
    """)
    assert PITFALL not in _ids(art)


def test_silent_no_ui_vocab():
    """Pure backend spec with no UI vocabulary → silent."""
    art = _spec("""
        ## Requirements

        FR-001: The system shall store records in PostgreSQL.
        FR-002: The API shall enforce JWT authentication.
        FR-003: The worker shall process background jobs.
    """)
    assert PITFALL not in _ids(art)


def test_silent_fewer_than_3_reqs():
    """Spec with <3 FR-/NFR- lines → silent even with UI vocab."""
    art = _spec("""
        ## Overview

        This is a React-based dashboard.

        FR-001: The React app shall render charts.
        FR-002: The system shall query the API.
    """)
    assert PITFALL not in _ids(art)


def test_silent_ui_in_fenced_block():
    """UI vocab only inside fenced code block → no trigger → silent."""
    art = _spec("""
        ## Requirements

        FR-001: The system shall process data.
        FR-002: The system shall store data.
        FR-003: The system shall send alerts.

        ```js
        // React component example
        const App = () => <div>Hello</div>;
        ```
    """)
    assert PITFALL not in _ids(art)


def test_silent_section508_present():
    """Section 508 reference → silent."""
    art = _spec("""
        ## Requirements

        FR-001: The web app shall display user profiles.
        FR-002: The frontend shall support search.
        FR-003: The system shall authenticate users.
        NFR-A1: The application shall comply with Section 508.
    """)
    assert PITFALL not in _ids(art)


def test_silent_plan_artifact():
    """Plan artifact with UI vocab → spec-only check → silent."""
    art = _plan("""
        ## Deployment

        FR-001: Deploy the React frontend to S3.
        FR-002: Configure the CDN for the SPA.
        FR-003: Set up the API gateway.
    """)
    assert PITFALL not in _ids(art)


def test_silent_ui_only_in_heading():
    """UI vocab in a heading only (not a non-heading line) → no trigger → silent."""
    art = _spec("""
        ## React Frontend Requirements

        FR-001: The system shall authenticate users.
        FR-002: The API shall return JSON responses.
        FR-003: The system shall store data securely.
    """)
    assert PITFALL not in _ids(art)
