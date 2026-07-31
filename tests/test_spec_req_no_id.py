"""Tests for the SPEC-REQ-NO-ID pitfall (normative req line missing a formal identifier)."""
from __future__ import annotations

import textwrap

from sddgrade.adapters.base import parse_sections
from sddgrade.catalog import load_catalog
from sddgrade.engine.lint import _req_no_id
from sddgrade.model import Artifact, ArtifactType

CATALOG = load_catalog()
PITFALL = "SPEC-REQ-NO-ID"


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
    return [f.pitfall_id for f in _req_no_id(art, CATALOG)]


# ── fires cases ───────────────────────────────────────────────────────────────

def test_shall_line_no_id_fires():
    """A 'shall' line in a Requirements section with no FR-/NFR-/AC-/US- ID fires."""
    art = _spec("""
        ## Requirements

        FR-001: The system shall authenticate users via OAuth 2.0.
        The system shall validate the JWT signature before granting access.
    """)
    assert PITFALL in _ids(art)


def test_must_line_no_id_fires():
    """A 'must' line in a Requirements section with no ID fires."""
    art = _spec("""
        ## Requirements

        FR-001: The system shall expose a REST API.
        Responses must be returned within 200ms under normal load.
    """)
    assert PITFALL in _ids(art)


def test_multiple_unlabeled_lines_counted():
    """Multiple shall/must lines without IDs produce a single aggregate finding."""
    art = _spec("""
        ## Requirements

        FR-001: The system shall support user login.
        The system shall encrypt passwords at rest.
        The system shall log all authentication events.
    """)
    findings = _req_no_id(art, CATALOG)
    assert findings
    assert findings[0].pitfall_id == PITFALL
    assert "2" in findings[0].message


def test_acceptance_section_shall_no_id_fires():
    """Acceptance-criteria section with unlabeled shall line fires."""
    art = _spec("""
        ## Acceptance Criteria

        AC-001: Given logged in, when the user clicks export, the CSV shall download.
        The download shall complete within 5 seconds.
    """)
    assert PITFALL in _ids(art)


def test_scenario_section_must_no_id_fires():
    """Scenario section with unlabeled must line fires."""
    art = _spec("""
        ## Scenarios

        AC-001: The payment flow must complete within 3 seconds.
        Error responses must include a machine-readable error code.
    """)
    assert PITFALL in _ids(art)


def test_first_offending_line_anchored():
    """The finding is anchored to the first offending line number."""
    art = _spec("""
        ## Requirements

        FR-001: The system shall expose a health endpoint.
        The system shall return 200 for successful checks.
        The system shall return 503 when dependencies are unhealthy.
    """)
    findings = _req_no_id(art, CATALOG)
    assert findings
    # The first unlabeled line is the second content line.
    assert findings[0].line > 1


def test_finding_message_contains_pitfall_id():
    """The finding message includes SPEC-REQ-NO-ID."""
    art = _spec("""
        ## Requirements

        FR-001: The system shall support exports.
        The system shall handle CSV and JSON formats.
    """)
    findings = _req_no_id(art, CATALOG)
    assert findings
    assert PITFALL in findings[0].message


# ── no-fire cases ─────────────────────────────────────────────────────────────

def test_no_fire_all_lines_have_fr_id():
    """Every shall/must line in the section carries an FR-NNN ID — silent."""
    art = _spec("""
        ## Requirements

        FR-001: The system shall authenticate users via OAuth 2.0.
        FR-002: The system shall support password reset via email.
        FR-003: The system shall lock accounts after 5 failed attempts.
    """)
    assert PITFALL not in _ids(art)


def test_no_fire_nfr_id_present():
    """Lines with NFR-NNN are silent."""
    art = _spec("""
        ## Requirements

        NFR-01: The API must respond within 200ms at p95.
        NFR-02: The system must achieve 99.9% uptime.
    """)
    assert PITFALL not in _ids(art)


def test_no_fire_ac_id_present():
    """Lines with AC-NNN are silent."""
    art = _spec("""
        ## Acceptance Criteria

        AC-001: Given authenticated, when requesting data, the system shall return 200.
        AC-002: The payload must include the user's email address.
    """)
    assert PITFALL not in _ids(art)


def test_no_fire_us_id_present():
    """Lines with US-NNN are silent."""
    art = _spec("""
        ## Requirements

        US-001: As a user I shall be able to download my data.
        US-002: Users must receive email confirmation after signup.
    """)
    assert PITFALL not in _ids(art)


def test_no_fire_section_has_no_modals():
    """Pure-prose section (no shall/must) is skipped — SPEC-REQ-SECTION-PROSE-ONLY covers it."""
    art = _spec("""
        ## Requirements

        The system handles authentication via session cookies.
        Sessions expire after 24 hours of inactivity.
    """)
    assert PITFALL not in _ids(art)


def test_no_fire_non_requirements_section():
    """shall/must in a non-requirements section (Overview) does not fire."""
    art = _spec("""
        ## Overview

        This feature shall integrate with the existing OAuth provider.
        Users must consent to the privacy policy on first login.
    """)
    assert PITFALL not in _ids(art)


def test_no_fire_fenced_block_excluded():
    """Unlabeled shall/must inside a fenced code block is not counted."""
    art = _spec("""
        ## Requirements

        FR-001: The system shall validate inputs.

        ```
        # The system shall not allow SQL injection — example comment
        must = True
        ```
    """)
    assert PITFALL not in _ids(art)


def test_no_fire_heading_line_excluded():
    """Section headings themselves are not scanned for unlabeled shall/must."""
    art = _spec("""
        ## Requirements shall be Labeled

        FR-001: The system shall authenticate users.
        FR-002: Passwords must be hashed with bcrypt.
    """)
    assert PITFALL not in _ids(art)


def test_no_fire_plan_artifact():
    """Does not fire on plan.md (applies to spec only)."""
    plan = _plan("""
        ## Requirements

        The deployment shall use blue-green switching.
        Rollbacks must complete within 5 minutes.
    """)
    assert PITFALL not in _ids(plan)


def test_single_finding_per_artifact():
    """Multiple unlabeled lines produce exactly one aggregate finding."""
    art = _spec("""
        ## Requirements

        FR-001: The system shall expose a REST API.
        The system shall authenticate requests via bearer tokens.
        The system shall rate-limit to 100 RPS per client.

        ## Acceptance Criteria

        AC-001: Given a valid token, when the endpoint is called, the system shall respond 200.
        The response must include the request-id header.
    """)
    findings = _req_no_id(art, CATALOG)
    assert len(findings) == 1
    assert PITFALL in findings[0].pitfall_id
