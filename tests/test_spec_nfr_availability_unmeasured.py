"""Tests for SPEC-NFR-AVAILABILITY-UNMEASURED pitfall.

A normative requirement line (shall/must/FR-/NFR-) that contains a qualitative
availability claim ('highly available', 'always available', '24/7', 'always-on',
'continuously available', 'non-stop', 'round-the-clock') but no numeric SLA
percentage fires this check.  When a numeric SLA is present on the same line
(99.9%, four nines, etc.) the check is SILENT.

Source: ISO/IEC/IEEE 29148:2018 §5.2.5(a); Canon Volere §9 Fit Criterion;
        MAQA binary-verifiability criterion; QVscribe Level-1 Clarity.
"""
from __future__ import annotations

import textwrap

from sddgrade.adapters.base import parse_sections
from sddgrade.catalog import load_catalog
from sddgrade.engine.lint import _spec_nfr_availability_unmeasured
from sddgrade.model import Artifact, ArtifactType

CATALOG = load_catalog()
PITFALL = "SPEC-NFR-AVAILABILITY-UNMEASURED"


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
    return [f.pitfall_id for f in _spec_nfr_availability_unmeasured(art, CATALOG)]


# ── fires cases ──────────────────────────────────────────────────────────────


def test_fires_highly_available_no_sla():
    """'highly available' with no numeric SLA → fires."""
    art = _spec("""
        ## Requirements

        - NFR-001: The system shall be highly available.
        - FR-001: The system shall authenticate users.
        - FR-002: The system shall log events.
        - FR-003: The system shall send notifications.
    """)
    assert PITFALL in _ids(art)


def test_fires_always_available_no_sla():
    """'always available' with no numeric SLA → fires."""
    art = _spec("""
        ## Requirements

        - NFR-001: The service shall be always available to registered users.
        - FR-001: The system shall handle login.
        - FR-002: The system shall handle logout.
        - FR-003: The system shall refresh tokens.
    """)
    assert PITFALL in _ids(art)


def test_fires_24_7_no_sla():
    """'24/7' with no numeric SLA → fires."""
    art = _spec("""
        ## Non-Functional Requirements

        NFR-001: The platform shall be available 24/7 without interruption.

        ## Functional Requirements

        - FR-001: The system shall process payments.
        - FR-002: The system shall refund orders.
        - FR-003: The system shall generate invoices.
    """)
    assert PITFALL in _ids(art)


def test_fires_always_on_no_sla():
    """'always-on' with no numeric SLA → fires."""
    art = _spec("""
        ## Requirements

        - NFR-001: The API must be always-on for critical operations.
        - FR-001: The system shall accept POST requests.
        - FR-002: The system shall validate payloads.
        - FR-003: The system shall return structured errors.
    """)
    assert PITFALL in _ids(art)


def test_fires_non_stop_no_sla():
    """'non-stop' with no numeric SLA → fires."""
    art = _spec("""
        ## Requirements

        - NFR-001: The data pipeline shall run non-stop to ingest events.
        - FR-001: The system shall consume from Kafka.
        - FR-002: The system shall write to the data warehouse.
        - FR-003: The system shall alert on lag.
    """)
    assert PITFALL in _ids(art)


def test_fires_round_the_clock_no_sla():
    """'round-the-clock' with no numeric SLA → fires."""
    art = _spec("""
        ## Requirements

        - NFR-001: The monitoring dashboard shall be round-the-clock accessible.
        - FR-001: The system shall display metrics.
        - FR-002: The system shall allow drill-down.
        - FR-003: The system shall export reports.
    """)
    assert PITFALL in _ids(art)


def test_fires_continuously_available_no_sla():
    """'continuously available' with no numeric SLA → fires."""
    art = _spec("""
        ## Non-Functional Requirements

        - NFR-001: The API shall be continuously available to downstream consumers.

        ## Functional Requirements

        - FR-001: The system shall expose a REST API.
        - FR-002: The system shall support JSON.
        - FR-003: The system shall version endpoints.
    """)
    assert PITFALL in _ids(art)


# ── silent cases ─────────────────────────────────────────────────────────────


def test_silent_highly_available_with_numeric_sla():
    """'highly available' followed by '99.9%' on same line → silent."""
    art = _spec("""
        ## Requirements

        - NFR-001: The system shall be highly available, targeting 99.9% uptime per month.
        - FR-001: The system shall serve requests.
        - FR-002: The system shall failover automatically.
        - FR-003: The system shall emit health metrics.
    """)
    assert PITFALL not in _ids(art)


def test_silent_always_available_with_four_nines():
    """'always available' with 'four nines' on same line → silent."""
    art = _spec("""
        ## Requirements

        - NFR-001: The service shall be always available (four nines: 99.99% uptime).
        - FR-001: The system shall handle API requests.
        - FR-002: The system shall log all errors.
        - FR-003: The system shall support retries.
    """)
    assert PITFALL not in _ids(art)


def test_silent_24x7_with_numeric_uptime():
    """'24x7' with '99.5% uptime' on same line → silent."""
    art = _spec("""
        ## Requirements

        - NFR-001: The system must be available 24x7 with 99.5% uptime.
        - FR-001: The system shall process transactions.
        - FR-002: The system shall store audit records.
        - FR-003: The system shall enforce rate limits.
    """)
    assert PITFALL not in _ids(art)


def test_silent_no_availability_claim():
    """Spec with no qualitative availability claim → silent."""
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

        - The service shall be highly available.
        - Deploy with three replicas across availability zones.
        - Monitor with Datadog.
    """)
    assert PITFALL not in _ids(art)


def test_silent_fenced_block_excluded():
    """Availability claim inside fenced code block → silent."""
    art = _spec("""
        ## Requirements

        - FR-001: The system shall authenticate users.
        - FR-002: The system shall log events.
        - FR-003: The system shall support OAuth.

        ```yaml
        # NFR-001: system shall be highly available
        replicas: 3
        ```
    """)
    assert PITFALL not in _ids(art)


def test_silent_five_nines_on_same_line():
    """'non-stop' with 'five nines' on same line → silent."""
    art = _spec("""
        ## Requirements

        - NFR-001: The service shall be non-stop, meeting five nines (99.999%) uptime.
        - FR-001: The system shall accept requests.
        - FR-002: The system shall queue overflow.
        - FR-003: The system shall drain gracefully.
    """)
    assert PITFALL not in _ids(art)


def test_silent_three_nines_on_same_line():
    """'always-on' with 'three nines' on same line → silent."""
    art = _spec("""
        ## Requirements

        - NFR-001: The system must be always-on (three nines, 99.9% per quarter).
        - FR-001: The system shall serve traffic.
        - FR-002: The system shall restart workers on crash.
        - FR-003: The system shall report uptime to the SRE dashboard.
    """)
    assert PITFALL not in _ids(art)


def test_silent_no_requirements():
    """Spec with no requirement-bearing lines → silent."""
    art = _spec("""
        ## Overview

        This spec describes the new payment gateway integration.

        ## Background

        We need to improve transaction reliability.
    """)
    assert PITFALL not in _ids(art)


def test_single_finding_returned():
    """Only one aggregate finding returned even with multiple offending lines."""
    art = _spec("""
        ## Requirements

        - NFR-001: The system shall be highly available.
        - NFR-002: The service must be available 24/7.
        - FR-001: The system shall handle load.
        - FR-002: The system shall log requests.
        - FR-003: The system shall support retries.
    """)
    findings = _spec_nfr_availability_unmeasured(art, CATALOG)
    assert len(findings) == 1
    assert findings[0].pitfall_id == PITFALL
