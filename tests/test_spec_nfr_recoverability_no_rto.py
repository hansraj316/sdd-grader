"""Tests for SPEC-NFR-RECOVERABILITY-NO-RTO pitfall.

Fires when a normative NFR line in a spec asserts disaster-recovery,
fault-tolerance, failover, or recoverability without a measurable RTO or RPO.
Source: ISO 25010 Recoverability; Canon Volere Scale/Meter/Must;
        ISO 29148 §5.2.5(i); Kiro production-readiness.
"""
from __future__ import annotations

import textwrap

from sddgrade.adapters.base import parse_sections
from sddgrade.catalog import load_catalog
from sddgrade.engine.lint import _spec_nfr_recoverability_no_rto
from sddgrade.model import Artifact, ArtifactType

CATALOG = load_catalog()
PITFALL = "SPEC-NFR-RECOVERABILITY-NO-RTO"


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
    return [f.pitfall_id for f in _spec_nfr_recoverability_no_rto(art, CATALOG)]


# ---------------------------------------------------------------------------
# FIRE cases
# ---------------------------------------------------------------------------

def test_fires_disaster_recovery_no_rto():
    art = _spec("""
        ## Requirements

        - NFR-001: The system shall support disaster recovery with no downtime.
    """)
    assert PITFALL in _ids(art)


def test_fires_fault_tolerant_no_rpo():
    art = _spec("""
        ## Requirements

        - NFR-002: The system must be fault-tolerant across availability zones.
    """)
    assert PITFALL in _ids(art)


def test_fires_failover_no_rto():
    art = _spec("""
        ## Requirements

        - NFR-003: The database shall support automatic failover in the event of node failure.
    """)
    assert PITFALL in _ids(art)


def test_fires_recoverable_no_rto():
    art = _spec("""
        ## Requirements

        - NFR-004: The system shall be recoverable after a catastrophic failure.
    """)
    assert PITFALL in _ids(art)


def test_fires_business_continuity_no_rpo():
    art = _spec("""
        ## Requirements

        - NFR-005: The platform must meet business continuity requirements for all core services.
    """)
    assert PITFALL in _ids(art)


def test_fires_self_healing_no_rto():
    art = _spec("""
        ## Requirements

        - NFR-006: The microservice cluster shall be self-healing, restarting failed pods.
    """)
    assert PITFALL in _ids(art)


def test_fires_active_passive_no_rto():
    art = _spec("""
        ## Requirements

        - NFR-007: The system shall use active-passive replication for high availability.
    """)
    assert PITFALL in _ids(art)


# ---------------------------------------------------------------------------
# SILENT cases
# ---------------------------------------------------------------------------

def test_silent_rto_present():
    art = _spec("""
        ## Requirements

        - NFR-010: The system shall support failover with an RTO of ≤ 15 minutes.
    """)
    assert PITFALL not in _ids(art)


def test_silent_rpo_present():
    art = _spec("""
        ## Requirements

        - NFR-011: The system must be fault-tolerant. RPO: zero data loss for committed transactions.
    """)
    assert PITFALL not in _ids(art)


def test_silent_recovery_time_objective_spelled_out():
    art = _spec("""
        ## Requirements

        - NFR-012: The system shall support disaster recovery. Recovery time objective: 4 hours.
    """)
    assert PITFALL not in _ids(art)


def test_silent_numeric_time_unit():
    art = _spec("""
        ## Requirements

        - NFR-013: The system shall be recoverable within 30 minutes of a failure event.
    """)
    assert PITFALL not in _ids(art)


def test_silent_zero_data_loss():
    art = _spec("""
        ## Requirements

        - NFR-014: The system shall support active-active replication with zero data loss.
    """)
    assert PITFALL not in _ids(art)


def test_silent_no_recovery_vocab():
    art = _spec("""
        ## Requirements

        - NFR-015: The system shall respond to API requests within 200ms at the 99th percentile.
    """)
    assert PITFALL not in _ids(art)


def test_silent_non_normative_prose():
    art = _spec("""
        ## Design Notes

        The system will use failover for redundancy.
    """)
    assert PITFALL not in _ids(art)


def test_silent_fenced_block():
    art = _spec("""
        ## Requirements

        ```
        NFR-016: The system shall support disaster recovery.
        ```
    """)
    assert PITFALL not in _ids(art)


def test_silent_non_spec_artifact():
    art = _plan("""
        ## Requirements

        - NFR-001: The system shall support failover.
    """)
    assert PITFALL not in _ids(art)


def test_silent_mttr_present():
    art = _spec("""
        ## Requirements

        - NFR-017: The system shall be self-healing with MTTR ≤ 5 minutes.
    """)
    assert PITFALL not in _ids(art)
