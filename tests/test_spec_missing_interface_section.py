"""Tests for SPEC-MISSING-INTERFACE-SECTION pitfall.

Fires when a spec.md has ≥5 non-fenced normative lines (shall/must/FR-/NFR-)
AND ≥1 FR-NNN line but no section heading that matches an interface-class keyword
(Interface, External Interface, External System, External API, Integration Point,
API Contract, System Boundary, System Interface).

Sources: ISO/IEC/IEEE 29148:2018 §9.6.5.3; IEEE 830-1998 §3.2.
"""
from __future__ import annotations

import textwrap

from sddgrade.adapters.base import parse_sections
from sddgrade.catalog import load_catalog
from sddgrade.engine.lint import _spec_missing_interface_section
from sddgrade.model import Artifact, ArtifactType

CATALOG = load_catalog()
PITFALL = "SPEC-MISSING-INTERFACE-SECTION"


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


def _tasks(raw: str) -> Artifact:
    raw = textwrap.dedent(raw).strip()
    return Artifact(
        path="tasks.md",
        type=ArtifactType.TASKS,
        feature_id="test",
        raw=raw,
        sections=parse_sections(raw),
    )


def _ids(art: Artifact) -> list[str]:
    return [f.pitfall_id for f in _spec_missing_interface_section(art, CATALOG)]


# ---------------------------------------------------------------------------
# FIRE cases
# ---------------------------------------------------------------------------


def test_fires_five_fr_lines_no_interface():
    """Spec with 5 FR- lines and no interface section fires."""
    art = _spec("""
        # Feature Spec

        ## Requirements
        FR-001: The system shall authenticate users.
        FR-002: The system shall issue JWT tokens.
        FR-003: The system shall revoke sessions.
        FR-004: The system shall refresh tokens.
        FR-005: The system shall audit login attempts.
    """)
    assert PITFALL in _ids(art)


def test_fires_mixed_shall_and_fr():
    """Guard counts both shall lines and explicit FR- IDs."""
    art = _spec("""
        # Feature Spec

        ## Requirements
        FR-001: The system shall process payments.
        The system shall validate card numbers.
        The system shall apply discounts.
        FR-002: The system shall emit receipts.
        FR-003: The system shall support refunds.
    """)
    assert PITFALL in _ids(art)


def test_fires_interface_word_only_in_prose():
    """'interface' appearing in prose body, not as a heading, does not silence."""
    art = _spec("""
        # Feature Spec

        The system uses an interface-first design approach for all components.

        ## Requirements
        FR-001: The system shall export tasks.
        FR-002: The system shall filter by status.
        FR-003: The system shall escape field values.
        FR-004: The system shall support pagination.
        FR-005: The system shall stream large exports.
    """)
    assert PITFALL in _ids(art)


def test_fires_scope_heading_not_enough():
    """A Scope section does not satisfy the Interfaces requirement."""
    art = _spec("""
        # Feature Spec

        ## Scope
        Covers the CSV export feature.

        ## Requirements
        FR-001: The system shall export tasks.
        FR-002: The system shall filter by status.
        FR-003: The system shall escape field values.
        FR-004: The system shall validate dates.
        FR-005: The system shall paginate results.
    """)
    assert PITFALL in _ids(art)


# ---------------------------------------------------------------------------
# SILENT cases
# ---------------------------------------------------------------------------


def test_silent_external_interfaces_heading():
    """'## External Interfaces' heading silences the check."""
    art = _spec("""
        # Feature Spec

        ## External Interfaces
        - Export API (REST/JSON): outbound CSV download.

        ## Requirements
        FR-001: The system shall export tasks.
        FR-002: The system shall filter by status.
        FR-003: The system shall escape CSV values.
        FR-004: The system shall validate export requests.
        FR-005: The system shall return 404 for missing features.
    """)
    assert PITFALL not in _ids(art)


def test_silent_integration_points_heading():
    """'## Integration Points' heading silences the check."""
    art = _spec("""
        # Feature Spec

        ## Integration Points
        - Auth service (OAuth2 bearer token).

        ## Requirements
        FR-001: The system shall authenticate.
        FR-002: The system shall issue sessions.
        FR-003: The system shall revoke sessions.
        FR-004: The system shall audit logins.
        FR-005: The system shall enforce MFA.
    """)
    assert PITFALL not in _ids(art)


def test_silent_api_contracts_heading():
    """'## API Contracts' heading silences the check."""
    art = _spec("""
        # Feature Spec

        ## API Contracts
        - POST /export (Bearer token auth).

        ## Requirements
        FR-001: The system shall expose an export endpoint.
        FR-002: The system shall validate the request body.
        FR-003: The system shall stream the response.
        FR-004: The system shall return HTTP 200 on success.
        FR-005: The system shall return HTTP 400 on invalid input.
    """)
    assert PITFALL not in _ids(art)


def test_silent_system_interface_heading():
    """'## System Interface' heading satisfies the check."""
    art = _spec("""
        # Feature Spec

        ## System Interface
        - Notification service (gRPC/mTLS).

        ## Requirements
        FR-001: The system shall notify on completion.
        FR-002: The system shall retry on failure.
        FR-003: The system shall log errors.
        FR-004: The system shall support batch sends.
        FR-005: The system shall handle duplicates.
    """)
    assert PITFALL not in _ids(art)


def test_silent_fewer_than_five_normative():
    """Guard requires ≥5 normative lines; 4 is silent."""
    art = _spec("""
        # Feature Spec

        ## Requirements
        FR-001: The system shall export tasks.
        FR-002: The system shall filter by status.
        FR-003: The system shall escape CSV values.
        FR-004: The system shall validate dates.
    """)
    assert PITFALL not in _ids(art)


def test_silent_nfr_only_no_fr():
    """Pure-NFR spec (no FR- IDs) is silenced even with ≥5 normative lines."""
    art = _spec("""
        # Feature Spec

        ## Requirements
        NFR-001: The system shall respond within 200 ms.
        NFR-002: The system shall handle 1000 requests per second.
        NFR-003: The system shall achieve 99.9% uptime.
        The system must encrypt all data at rest.
        The system must encrypt all data in transit.
    """)
    assert PITFALL not in _ids(art)


def test_silent_fenced_lines_excluded():
    """Normative lines inside fenced code blocks don't count toward the guard."""
    art = _spec("""
        # Feature Spec

        ## Requirements
        FR-001: The system shall do X.

        ```
        FR-002: The system shall do Y.
        FR-003: The system shall do Z.
        FR-004: The system shall do A.
        FR-005: The system shall do B.
        ```
    """)
    assert PITFALL not in _ids(art)


def test_silent_plan_artifact():
    """Plan artifacts are not checked."""
    art = _plan("""
        # Deployment Plan

        ## Steps
        FR-001: deploy step.
        FR-002: more steps.
        FR-003: rollback steps.
        FR-004: health check.
        FR-005: notify.
    """)
    assert PITFALL not in _ids(art)


def test_silent_tasks_artifact():
    """Tasks artifacts are not checked."""
    art = _tasks("""
        # Tasks

        ## Sprint
        FR-001 task.
        FR-002 task.
        FR-003 task.
        FR-004 task.
        FR-005 task.
    """)
    assert PITFALL not in _ids(art)


def test_silent_interface_heading_case_insensitive():
    """'## INTERFACES' (all caps) silences the check."""
    art = _spec("""
        # Feature Spec

        ## INTERFACES
        External REST API for task data.

        ## Requirements
        FR-001: The system shall export tasks.
        FR-002: The system shall filter by status.
        FR-003: The system shall escape CSV values.
        FR-004: The system shall validate dates.
        FR-005: The system shall paginate results.
    """)
    assert PITFALL not in _ids(art)
