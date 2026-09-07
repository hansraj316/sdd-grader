"""Tests for SPEC-NFR-PERCENT-CONTEXT-MISSING pitfall.

A non-functional requirement line that contains a percentage value ('%' or
'percent(age)') with no named metric noun fires this check.  When a metric noun
such as 'uptime', 'success rate', 'coverage', 'availability', etc. appears on
the same requirement line the check is SILENT.

Source: Canon Volere Scale/Meter/Must principle; QVscribe §QV-104 Clarity;
        ISO/IEC/IEEE 29148:2018 §5.2.5(a) Unambiguous.
"""
from __future__ import annotations

import textwrap

from sddgrade.adapters.base import parse_sections
from sddgrade.catalog import load_catalog
from sddgrade.engine.lint import _spec_nfr_percent_context_missing
from sddgrade.model import Artifact, ArtifactType

CATALOG = load_catalog()
PITFALL = "SPEC-NFR-PERCENT-CONTEXT-MISSING"


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
    return [f.pitfall_id for f in _spec_nfr_percent_context_missing(art, CATALOG)]


# ── fires cases ──────────────────────────────────────────────────────────────


def test_fires_bare_percent_no_metric():
    """NFR line with '99.9%' and no metric noun → fires."""
    art = _spec("""
        ## Requirements

        - NFR-001: The system shall achieve 99.9%.
        - NFR-002: The system shall respond within 200ms.
        - FR-001: The system shall do something.
        - FR-002: The system shall do another thing.
        - FR-003: The system shall do a third thing.
    """)
    assert PITFALL in _ids(art)


def test_fires_percent_word_no_metric():
    """'95 percent' with no metric noun → fires."""
    art = _spec("""
        ## Requirements

        - NFR-001: The system shall achieve 95 percent.
        - FR-001: The system shall process requests.
        - FR-002: The system shall log errors.
        - FR-003: The system shall support retries.
    """)
    assert PITFALL in _ids(art)


def test_fires_percentage_word_no_metric():
    """'99 percentage' with no metric noun → fires."""
    art = _spec("""
        ## Requirements

        - NFR-001: The API shall maintain 99 percentage at all times.
        - FR-001: The system shall handle requests.
        - FR-002: The system shall validate input.
        - FR-003: The system shall return JSON.
    """)
    assert PITFALL in _ids(art)


def test_fires_shall_requirement_with_bare_pct():
    """'shall be at least 80%' with no metric context → fires."""
    art = _spec("""
        ## Non-Functional Requirements

        NFR-001: The service shall be at least 80%.

        ## Functional Requirements

        - FR-001: The system shall authenticate users.
        - FR-002: The system shall log events.
        - FR-003: The system shall send notifications.
    """)
    assert PITFALL in _ids(art)


def test_fires_must_with_bare_pct():
    """'must exceed 99%' with no metric → fires."""
    art = _spec("""
        ## Requirements

        - NFR-001: The system must exceed 99%.
        - FR-001: The system shall handle requests.
        - FR-002: The system shall support batching.
        - FR-003: The system shall emit events.
    """)
    assert PITFALL in _ids(art)


def test_fires_fr_line_with_bare_pct():
    """FR- line with bare % (no metric) → fires (req_mask covers FR lines too)."""
    art = _spec("""
        ## Requirements

        - FR-001: The system shall shall be operational at 99.5%.
        - FR-002: The system shall handle concurrent users.
        - FR-003: The system shall log all transactions.
        - FR-004: The system shall reject bad input.
    """)
    assert PITFALL in _ids(art)


# ── silent cases ─────────────────────────────────────────────────────────────


def test_silent_uptime_present():
    """'99.9% uptime' → silent (metric named)."""
    art = _spec("""
        ## Requirements

        - NFR-001: The system shall maintain 99.9% uptime.
        - FR-001: The system shall process requests.
        - FR-002: The system shall log errors.
        - FR-003: The system shall support retries.
    """)
    assert PITFALL not in _ids(art)


def test_silent_availability_present():
    """'99% availability' → silent."""
    art = _spec("""
        ## Requirements

        - NFR-001: The system shall achieve 99% availability during peak hours.
        - FR-001: The system shall authenticate users.
        - FR-002: The system shall log events.
        - FR-003: The system shall send alerts.
    """)
    assert PITFALL not in _ids(art)


def test_silent_success_rate_present():
    """'95% success rate' → silent."""
    art = _spec("""
        ## Requirements

        - NFR-001: The API shall achieve a 95% success rate under peak load.
        - FR-001: The system shall validate requests.
        - FR-002: The system shall route requests.
        - FR-003: The system shall retry on transient errors.
    """)
    assert PITFALL not in _ids(art)


def test_silent_coverage_present():
    """'80% coverage' → silent."""
    art = _spec("""
        ## Requirements

        - NFR-001: Test coverage shall reach 80% coverage.
        - FR-001: The system shall handle login.
        - FR-002: The system shall handle logout.
        - FR-003: The system shall refresh tokens.
    """)
    assert PITFALL not in _ids(art)


def test_silent_error_rate_present():
    """'error rate below 1%' → silent (metric noun present)."""
    art = _spec("""
        ## Requirements

        - NFR-001: The system shall keep error rate below 1%.
        - FR-001: The system shall process events.
        - FR-002: The system shall emit metrics.
        - FR-003: The system shall support pagination.
    """)
    assert PITFALL not in _ids(art)


def test_silent_throughput_present():
    """'throughput of 99%' → silent."""
    art = _spec("""
        ## Requirements

        - NFR-001: The system shall achieve throughput of 99% of rated capacity.
        - FR-001: The system shall handle write requests.
        - FR-002: The system shall handle read requests.
        - FR-003: The system shall cache frequently accessed data.
    """)
    assert PITFALL not in _ids(art)


def test_silent_slo_present():
    """'SLO of 99.5%' → silent (SLO is a metric context)."""
    art = _spec("""
        ## Requirements

        - NFR-001: The service shall meet its SLO of 99.5%.
        - FR-001: The system shall serve API requests.
        - FR-002: The system shall reject malformed input.
        - FR-003: The system shall rate-limit callers.
    """)
    assert PITFALL not in _ids(art)


def test_silent_reliability_present():
    """'reliability of 99.99%' → silent."""
    art = _spec("""
        ## Requirements

        - NFR-001: The system shall achieve reliability of 99.99%.
        - FR-001: The system shall replicate data.
        - FR-002: The system shall failover automatically.
        - FR-003: The system shall checkpoint state.
    """)
    assert PITFALL not in _ids(art)


def test_silent_plan_artifact_skipped():
    """Plan artifact is skipped regardless of content."""
    art = _plan("""
        ## Deployment

        - Deploy the service.
        - The service shall achieve 99.9%.
        - Monitor with Datadog.
    """)
    assert PITFALL not in _ids(art)


def test_silent_no_requirements():
    """Spec with no requirement-bearing lines → silent."""
    art = _spec("""
        ## Overview

        This spec describes the new payment service.

        ## Background

        We need to improve reliability.
    """)
    assert PITFALL not in _ids(art)


def test_silent_fenced_block_excluded():
    """Percentage in a fenced code block → silent."""
    art = _spec("""
        ## Requirements

        - FR-001: The system shall authenticate users.
        - FR-002: The system shall log events.
        - FR-003: The system shall support OAuth.

        ```python
        # NFR-001: The system shall achieve 99.9%.
        threshold = 0.999
        ```
    """)
    assert PITFALL not in _ids(art)


def test_single_finding_returned():
    """Only one aggregate finding is returned even with multiple offending lines."""
    art = _spec("""
        ## Requirements

        - NFR-001: The system shall achieve 99.9%.
        - NFR-002: The system shall achieve 95%.
        - FR-001: The system shall handle load.
        - FR-002: The system shall log requests.
        - FR-003: The system shall support retries.
    """)
    findings = _spec_nfr_percent_context_missing(art, CATALOG)
    assert len(findings) == 1
    assert findings[0].pitfall_id == PITFALL
