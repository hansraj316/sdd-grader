"""Tests for REQ-DUPLICATE-ID — duplicate requirement identifiers in spec.md."""
from __future__ import annotations

import textwrap

from sddgrade.adapters.base import parse_sections
from sddgrade.catalog import load_catalog
from sddgrade.engine.lint import _req_duplicate_id
from sddgrade.model import Artifact, ArtifactType

CATALOG = load_catalog()
PITFALL = "REQ-DUPLICATE-ID"


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


def ids(findings):
    return [f.pitfall_id for f in findings]


# --- fire cases ---

def test_duplicate_fr_id_fires():
    art = _spec("""
        # Spec

        ## Requirements
        - FR-001: The system shall log in users.
        - FR-002: The system shall log out users.
        - FR-001: The system shall also remember passwords.
    """)
    findings = _req_duplicate_id(art, CATALOG)
    assert PITFALL in ids(findings)


def test_duplicate_nfr_id_fires():
    art = _spec("""
        # Spec

        ## Requirements
        - NFR-001: Response time shall be under 200ms.
        - NFR-001: Uptime shall be 99.9%.
    """)
    findings = _req_duplicate_id(art, CATALOG)
    assert PITFALL in ids(findings)


def test_duplicate_ac_id_fires():
    art = _spec("""
        # Spec

        ## Acceptance Criteria
        - AC-001: Given login, when valid creds, then granted.
        - AC-002: Given logout, when clicked, then session cleared.
        - AC-001: Given login, when token expired, then redirect.
    """)
    findings = _req_duplicate_id(art, CATALOG)
    assert PITFALL in ids(findings)


def test_duplicate_us_id_fires():
    art = _spec("""
        # Spec

        - US-001: As a user, I want to log in, so that I can access my data.
        - US-001: As an admin, I want to reset passwords, so that I can help users.
    """)
    findings = _req_duplicate_id(art, CATALOG)
    assert PITFALL in ids(findings)


def test_message_includes_duplicate_id():
    art = _spec("""
        # Spec

        - FR-007: The system shall do X.
        - FR-007: The system shall also do Y.
    """)
    findings = _req_duplicate_id(art, CATALOG)
    assert findings
    assert "FR-007" in findings[0].message


def test_fires_exactly_once_per_artifact():
    art = _spec("""
        # Spec

        - FR-001: Requirement A.
        - FR-001: Requirement B.
        - FR-002: Requirement C.
        - FR-002: Requirement D.
    """)
    findings = _req_duplicate_id(art, CATALOG)
    assert len([f for f in findings if f.pitfall_id == PITFALL]) == 1


# --- silent cases ---

def test_all_unique_ids_silent():
    art = _spec("""
        # Spec

        ## Requirements
        - FR-001: The system shall log in users.
        - FR-002: The system shall log out users.
        - NFR-001: Response time shall be under 200ms.
    """)
    findings = _req_duplicate_id(art, CATALOG)
    assert PITFALL not in ids(findings)


def test_no_ids_at_all_silent():
    art = _spec("""
        # Spec

        ## Requirements
        - The system shall allow login.
        - The system shall allow logout.
    """)
    findings = _req_duplicate_id(art, CATALOG)
    assert PITFALL not in ids(findings)


def test_id_in_fenced_code_block_not_counted():
    art = _spec("""
        # Spec

        - FR-001: The system shall do X.

        ```
        FR-001: example reference in code block
        ```
    """)
    findings = _req_duplicate_id(art, CATALOG)
    assert PITFALL not in ids(findings)


def test_id_case_insensitive_collision():
    art = _spec("""
        # Spec

        - fr-001: The system shall do X.
        - FR-001: The system shall also do Y.
    """)
    findings = _req_duplicate_id(art, CATALOG)
    assert PITFALL in ids(findings)


def test_plan_artifact_skipped():
    """REQ-DUPLICATE-ID only applies to spec, not plan."""
    art = _plan("""
        # Plan

        - FR-001: implement login.
        - FR-001: also implement logout.
    """)
    findings = _req_duplicate_id(art, CATALOG)
    assert PITFALL not in ids(findings)


def test_blank_lines_not_counted():
    """Blank lines containing no ID should not affect the count."""
    art = _spec("""
        # Spec

        - FR-001: Requirement A.

        FR-001 is mentioned above.
    """)
    # "FR-001 is mentioned above" is a non-blank line — it IS a real occurrence.
    # So two non-blank lines have FR-001: should fire.
    findings = _req_duplicate_id(art, CATALOG)
    assert PITFALL in ids(findings)


def test_mixed_fr_nfr_no_collision_silent():
    """FR-001 and NFR-001 are different IDs — no collision."""
    art = _spec("""
        # Spec

        - FR-001: The system shall log in users.
        - NFR-001: Response time shall be under 200ms.
    """)
    findings = _req_duplicate_id(art, CATALOG)
    assert PITFALL not in ids(findings)
