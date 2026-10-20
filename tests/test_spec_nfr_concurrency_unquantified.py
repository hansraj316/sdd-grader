"""Tests for SPEC-NFR-CONCURRENCY-UNQUANTIFIED pitfall.

A normative requirement line (shall/must/FR-/NFR-) that contains a concurrency
or simultaneity claim ('concurrent users', 'simultaneous connections', 'parallel
requests', 'at the same time') but no numeric bound fires this check.  When a
numeric quantifier is present on the same line (e.g. '500 concurrent users', 'at
least 1,000 sessions') the check is SILENT.

Sources: ISO/IEC/IEEE 29148:2018 §5.2.5(a)/(i); QVscribe QV-104 (Imprecise
         Measurement); Canon Volere Scale/Meter/Must.
"""
from __future__ import annotations

import textwrap

from sddgrade.adapters.base import parse_sections
from sddgrade.catalog import load_catalog
from sddgrade.engine.lint import _spec_nfr_concurrency_unquantified
from sddgrade.model import Artifact, ArtifactType

CATALOG = load_catalog()
PITFALL = "SPEC-NFR-CONCURRENCY-UNQUANTIFIED"


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
    return [f.pitfall_id for f in _spec_nfr_concurrency_unquantified(art, CATALOG)]


# ── fires cases ──────────────────────────────────────────────────────────────


def test_fires_concurrent_users_no_number():
    """'concurrent users' with no numeric bound → fires."""
    art = _spec("""
        ## Requirements

        - NFR-001: The system shall support concurrent users without degradation.
        - FR-001: The system shall authenticate users.
        - FR-002: The system shall log requests.
        - FR-003: The system shall handle errors.
    """)
    assert PITFALL in _ids(art)


def test_fires_simultaneous_connections_no_number():
    """'simultaneous connections' with no numeric bound → fires."""
    art = _spec("""
        ## Non-Functional Requirements

        NFR-001: The database shall handle simultaneous connections from multiple services.

        ## Functional Requirements

        - FR-001: The system shall query user data.
        - FR-002: The system shall update records.
        - FR-003: The system shall delete stale data.
    """)
    assert PITFALL in _ids(art)


def test_fires_parallel_requests_no_number():
    """'parallel requests' with no numeric bound → fires."""
    art = _spec("""
        ## Requirements

        - NFR-001: The API must handle parallel requests from multiple clients.
        - FR-001: The system shall expose REST endpoints.
        - FR-002: The system shall validate inputs.
        - FR-003: The system shall return JSON responses.
    """)
    assert PITFALL in _ids(art)


def test_fires_concurrently_no_number():
    """'concurrently' adverb in requirement with no numeric bound → fires."""
    art = _spec("""
        ## Requirements

        - NFR-001: The system shall process tasks concurrently.
        - FR-001: The system shall queue jobs.
        - FR-002: The system shall retry on failure.
        - FR-003: The system shall log completion.
    """)
    assert PITFALL in _ids(art)


def test_fires_at_the_same_time_no_number():
    """'at the same time' in requirement with no numeric bound → fires."""
    art = _spec("""
        ## Requirements

        - NFR-001: The system shall serve multiple clients at the same time.
        - FR-001: The system shall route requests.
        - FR-002: The system shall cache responses.
        - FR-003: The system shall evict stale cache entries.
    """)
    assert PITFALL in _ids(art)


# ── silent cases ─────────────────────────────────────────────────────────────


def test_silent_concurrent_users_with_number():
    """'concurrent users' with explicit count → silent."""
    art = _spec("""
        ## Requirements

        - NFR-001: The system shall support 500 concurrent users at steady state.
        - FR-001: The system shall serve web traffic.
        - FR-002: The system shall failover automatically.
        - FR-003: The system shall emit health metrics.
    """)
    assert PITFALL not in _ids(art)


def test_silent_at_least_quantifier():
    """'at least 1,000 sessions' quantifier → silent."""
    art = _spec("""
        ## Requirements

        - NFR-001: The system must support at least 1000 simultaneous sessions.
        - FR-001: The system shall manage session tokens.
        - FR-002: The system shall expire idle sessions.
        - FR-003: The system shall log session events.
    """)
    assert PITFALL not in _ids(art)


def test_silent_maximum_quantifier():
    """'maximum 200 concurrent connections' → silent."""
    art = _spec("""
        ## Requirements

        - NFR-001: The service shall handle a maximum 200 concurrent connections.
        - FR-001: The system shall accept TCP connections.
        - FR-002: The system shall close idle connections.
        - FR-003: The system shall report connection count.
    """)
    assert PITFALL not in _ids(art)


def test_silent_no_concurrency_claim():
    """Spec with no concurrency vocabulary → silent."""
    art = _spec("""
        ## Requirements

        - NFR-001: The system shall respond within 200ms at p95.
        - FR-001: The system shall authenticate users via OAuth 2.0.
        - FR-002: The system shall log all failed requests.
        - FR-003: The system shall support pagination.
    """)
    assert PITFALL not in _ids(art)


def test_silent_plan_artifact_skipped():
    """Plan artifact is skipped regardless of content."""
    art = _plan("""
        ## Deployment Plan

        The system shall support concurrent users across multiple pods.
        Deploy with three replicas. Monitor with Datadog.
    """)
    assert PITFALL not in _ids(art)


def test_silent_fenced_block_excluded():
    """Concurrency claim inside fenced code block → silent."""
    art = _spec("""
        ## Requirements

        - FR-001: The system shall authenticate users.
        - FR-002: The system shall log events.
        - FR-003: The system shall support OAuth.

        ```yaml
        # NFR-001: system shall handle concurrent users
        replicas: 3
        ```
    """)
    assert PITFALL not in _ids(art)


def test_per_line_findings():
    """Each offending normative line produces its own finding."""
    art = _spec("""
        ## Requirements

        - NFR-001: The system shall support concurrent users.
        - NFR-002: The service must handle simultaneous connections.
        - FR-001: The system shall serve requests.
        - FR-002: The system shall log requests.
        - FR-003: The system shall support retries.
    """)
    findings = _spec_nfr_concurrency_unquantified(art, CATALOG)
    assert len(findings) == 2
    assert all(f.pitfall_id == PITFALL for f in findings)
