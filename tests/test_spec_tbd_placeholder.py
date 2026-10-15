"""Tests for SPEC-TBD-PLACEHOLDER pitfall.

Fires when a normative requirement line (scoped by _requirement_mask) contains
a TBD, TBC, TODO, or FIXME placeholder, indicating the requirement is incomplete.

Sources: ISO/IEC/IEEE 29148:2018 §5.2.4(a) completeness, IBM RQA Level-1 defect.
"""
from __future__ import annotations

import textwrap

from sddgrade.adapters.base import parse_sections
from sddgrade.catalog import load_catalog
from sddgrade.engine.lint import _spec_tbd_placeholder
from sddgrade.model import Artifact, ArtifactType

CATALOG = load_catalog()
PITFALL = "SPEC-TBD-PLACEHOLDER"


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
    return [f.pitfall_id for f in _spec_tbd_placeholder(art, CATALOG)]


# ---------------------------------------------------------------------------
# Firing cases — requirement lines with placeholders
# ---------------------------------------------------------------------------


def test_fires_tbd_in_fr_line():
    """FR- line with TBD fires."""
    art = _spec("""
        # Feature Spec

        ## Requirements

        FR-001: The system shall support TBD authentication methods.
        FR-002: The system shall respond within 200ms under normal load.
    """)
    ids = _ids(art)
    assert PITFALL in ids


def test_fires_todo_in_nfr_line():
    """NFR- line with TODO fires."""
    art = _spec("""
        # Feature Spec

        ## Requirements

        NFR-001: The system shall maintain TODO% uptime per month.
        FR-001: The system shall authenticate users via OAuth 2.0.
    """)
    ids = _ids(art)
    assert PITFALL in ids


def test_fires_tbc_in_shall_line():
    """shall line with TBC fires."""
    art = _spec("""
        # Feature Spec

        ## Requirements

        The system shall handle TBC edge cases gracefully.
    """)
    ids = _ids(art)
    assert PITFALL in ids


def test_fires_fixme_in_ac_line():
    """AC- line with FIXME fires."""
    art = _spec("""
        # Feature Spec

        ## Acceptance Criteria

        AC-001: Given a logged-in user, when FIXME, then the system logs out.
    """)
    ids = _ids(art)
    assert PITFALL in ids


def test_fires_multiple_lines_returns_multiple_findings():
    """Multiple requirement lines each with a placeholder produce multiple findings."""
    art = _spec("""
        # Feature Spec

        ## Requirements

        FR-001: The system shall support TBD authentication methods.
        FR-002: The system shall process TODO formats.
        FR-003: The system shall respond within 200ms.
    """)
    findings = _spec_tbd_placeholder(art, CATALOG)
    pitfall_findings = [f for f in findings if f.pitfall_id == PITFALL]
    assert len(pitfall_findings) == 2


def test_fires_case_insensitive_todo():
    """Case-insensitive match for 'todo' fires."""
    art = _spec("""
        # Feature Spec

        ## Requirements

        FR-001: The system shall provide todo integration.
    """)
    ids = _ids(art)
    assert PITFALL in ids


# ---------------------------------------------------------------------------
# Silent cases — no placeholder on requirement lines
# ---------------------------------------------------------------------------


def test_silent_no_placeholder():
    """Spec with no placeholders is silent."""
    art = _spec("""
        # Feature Spec

        ## Requirements

        FR-001: The system shall authenticate users via OAuth 2.0.
        FR-002: The system shall respond within 200ms at p95.
        FR-003: The system shall encrypt all data in transit via TLS 1.3.
    """)
    assert PITFALL not in _ids(art)


def test_silent_tbd_in_heading():
    """TBD in a heading line is not a requirement line and does not fire."""
    art = _spec("""
        # Feature Spec — TBD Scope

        ## Requirements

        FR-001: The system shall support OAuth 2.0.
        FR-002: The system shall log all access attempts.
    """)
    assert PITFALL not in _ids(art)


def test_silent_tbd_in_fenced_code_block():
    """TBD inside a fenced code block is ignored."""
    art = _spec("""
        # Feature Spec

        ## Requirements

        FR-001: The system shall validate inputs per the schema below.

        ```json
        {
          "auth_method": "TBD"
        }
        ```

        FR-002: The system shall return HTTP 400 for invalid payloads.
    """)
    assert PITFALL not in _ids(art)


def test_silent_tbd_in_inline_code():
    """TBD inside backtick inline code is ignored."""
    art = _spec("""
        # Feature Spec

        ## Requirements

        FR-001: The system shall not accept the literal string `TBD` as input.
        FR-002: The system shall authenticate users via OAuth 2.0.
    """)
    assert PITFALL not in _ids(art)


def test_silent_non_requirement_prose_with_tbd():
    """TBD in non-requirement prose section does not fire."""
    art = _spec("""
        # Feature Spec

        ## Background

        The rollout timeline is TBD pending stakeholder approval.

        ## Requirements

        FR-001: The system shall support OAuth 2.0 authentication.
        FR-002: The system shall respond within 200ms.
        FR-003: The system shall log all authentication attempts.
    """)
    assert PITFALL not in _ids(art)


def test_silent_plan_artifact():
    """Plan artifacts are not checked by this pitfall."""
    art = _plan("""
        # Deployment Plan

        ## Deployment

        Deploy the service. Auth method: TBD.

        FR-001: The system shall run on ECS.
    """)
    assert PITFALL not in _ids(art)
