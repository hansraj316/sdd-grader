"""Tests for SPEC-NFR-NO-UNIT pitfall.

Fires when a non-functional requirement line contains a numeric threshold but
no measurement unit — leaving the threshold unverifiable ("200 what?").

Guard: line matches _NFR_RE (latency/throughput/response time/uptime/availability/
scalability/concurrency/rps/performance/load-handling) AND _REQUIREMENTish_RE
(shall/must/FR-\\d/NFR-\\d) AND has a digit after stripping IDs.

Check: line has NO recognized unit (ms/sec/min/hour/day/percent/%/MB/GB/KB/TB/
GiB/MiB/KiB/bytes/rps/rpm/tps/qps/per second/per minute/per hour/vCPU/cores).

Sources:
  - Canon Scale/Meter/Must rule
  - QVscribe Level-1 Clarity — numeric-without-unit ambiguity defect
  - ISO/IEC/IEEE 29148:2018 §5.2.5(i) verifiable characteristic
  - Complements SPEC-NFR-NO-THRESHOLD (no number at all vs. number without unit)
"""

from __future__ import annotations

import pytest

from sddgrade.adapters.base import parse_sections
from sddgrade.catalog import load_catalog
from sddgrade.engine.lint import _spec_nfr_no_unit
from sddgrade.model import Artifact, ArtifactType


def _make_spec(raw: str) -> Artifact:
    return Artifact(
        path="spec.md",
        type=ArtifactType.SPEC,
        raw=raw,
        sections=parse_sections(raw),
    )


def _make_plan(raw: str) -> Artifact:
    return Artifact(
        path="plan.md",
        type=ArtifactType.PLAN,
        raw=raw,
        sections=parse_sections(raw),
    )


CATALOG = load_catalog()


# ---------------------------------------------------------------------------
# FIRE cases — check should trigger
# ---------------------------------------------------------------------------


def test_latency_no_unit_fires() -> None:
    """NFR with latency keyword + bare number and no unit → fires."""
    spec = _make_spec(
        "# Spec\n\n"
        "## Requirements\n\n"
        "- NFR-001: The system shall respond with latency under 200.\n"
    )
    findings = _spec_nfr_no_unit(spec, CATALOG)
    assert len(findings) == 1
    assert findings[0].pitfall_id == "SPEC-NFR-NO-UNIT"
    assert "unit" in findings[0].message.lower()


def test_throughput_no_unit_fires() -> None:
    """NFR with throughput keyword + bare number → fires."""
    spec = _make_spec(
        "# Spec\n\n"
        "## Requirements\n\n"
        "- NFR-002: The system must handle throughput of 1000.\n"
    )
    findings = _spec_nfr_no_unit(spec, CATALOG)
    assert len(findings) == 1
    assert findings[0].pitfall_id == "SPEC-NFR-NO-UNIT"


def test_uptime_no_unit_fires() -> None:
    """NFR with uptime keyword + bare decimal number and no % → fires."""
    spec = _make_spec(
        "# Spec\n\n"
        "## Requirements\n\n"
        "- NFR-003: The system shall maintain uptime of 99.9.\n"
    )
    findings = _spec_nfr_no_unit(spec, CATALOG)
    assert len(findings) == 1
    assert findings[0].pitfall_id == "SPEC-NFR-NO-UNIT"


def test_performance_no_unit_fires() -> None:
    """Performance keyword + number but no unit → fires."""
    spec = _make_spec(
        "# Spec\n\n"
        "## Requirements\n\n"
        "- FR-001: The API shall meet performance targets of 50 under load.\n"
    )
    findings = _spec_nfr_no_unit(spec, CATALOG)
    assert len(findings) == 1
    assert findings[0].pitfall_id == "SPEC-NFR-NO-UNIT"


def test_response_time_no_unit_fires() -> None:
    """Response time keyword + bare number → fires."""
    spec = _make_spec(
        "# Spec\n\n"
        "## Requirements\n\n"
        "- NFR-001: The endpoint shall have a response time below 300.\n"
    )
    findings = _spec_nfr_no_unit(spec, CATALOG)
    assert len(findings) == 1
    assert findings[0].pitfall_id == "SPEC-NFR-NO-UNIT"


def test_load_handling_no_unit_fires() -> None:
    """Load-handling keyword + bare number and no unit → fires."""
    spec = _make_spec(
        "# Spec\n\n"
        "## Requirements\n\n"
        "- NFR-004: The system shall support load handling up to 10000.\n"
    )
    findings = _spec_nfr_no_unit(spec, CATALOG)
    assert len(findings) == 1
    assert findings[0].pitfall_id == "SPEC-NFR-NO-UNIT"


def test_finding_anchored_to_offending_line() -> None:
    """Finding is anchored to the line containing the unqualified threshold."""
    raw = (
        "# Spec\n\n"
        "## Requirements\n\n"
        "- FR-001: The system shall process requests.\n"
        "- NFR-001: The system shall maintain uptime of 99 without incidents.\n"
    )
    spec = _make_spec(raw)
    findings = _spec_nfr_no_unit(spec, CATALOG)
    assert len(findings) == 1
    assert findings[0].line == 6  # line 6 is the NFR line


# ---------------------------------------------------------------------------
# SILENT cases — check must NOT trigger
# ---------------------------------------------------------------------------


def test_latency_with_ms_unit_silent() -> None:
    """Latency NFR with 'ms' unit → no finding."""
    spec = _make_spec(
        "# Spec\n\n"
        "## Requirements\n\n"
        "- NFR-001: The system shall respond with latency under 200ms.\n"
    )
    assert _spec_nfr_no_unit(spec, CATALOG) == []


def test_uptime_with_percent_silent() -> None:
    """Uptime NFR with '%' percentage unit → no finding."""
    spec = _make_spec(
        "# Spec\n\n"
        "## Requirements\n\n"
        "- NFR-001: The system shall maintain uptime of 99.9%.\n"
    )
    assert _spec_nfr_no_unit(spec, CATALOG) == []


def test_throughput_with_rps_silent() -> None:
    """Throughput NFR with 'rps' unit → no finding."""
    spec = _make_spec(
        "# Spec\n\n"
        "## Requirements\n\n"
        "- NFR-001: The system must support throughput of 500 rps.\n"
    )
    assert _spec_nfr_no_unit(spec, CATALOG) == []


def test_performance_per_second_silent() -> None:
    """Performance NFR with 'per second' → no finding."""
    spec = _make_spec(
        "# Spec\n\n"
        "## Requirements\n\n"
        "- NFR-001: The API shall handle 1000 requests per second under normal load.\n"
    )
    assert _spec_nfr_no_unit(spec, CATALOG) == []


def test_storage_nfr_with_mb_silent() -> None:
    """Performance NFR with MB unit → no finding."""
    spec = _make_spec(
        "# Spec\n\n"
        "## Requirements\n\n"
        "- NFR-001: The system shall keep memory below 512 MB under peak load.\n"
    )
    assert _spec_nfr_no_unit(spec, CATALOG) == []


def test_latency_with_milliseconds_silent() -> None:
    """Latency NFR with 'milliseconds' written out → no finding."""
    spec = _make_spec(
        "# Spec\n\n"
        "## Requirements\n\n"
        "- NFR-001: P95 latency shall remain under 150 milliseconds.\n"
    )
    assert _spec_nfr_no_unit(spec, CATALOG) == []


def test_no_digit_after_stripping_ids_silent() -> None:
    """NFR line with no numeric threshold (only IDs) — SPEC-NFR-NO-THRESHOLD case, not ours."""
    spec = _make_spec(
        "# Spec\n\n"
        "## Requirements\n\n"
        "- NFR-001: The system shall have low latency and high availability.\n"
    )
    assert _spec_nfr_no_unit(spec, CATALOG) == []


def test_no_nfr_keyword_silent() -> None:
    """FR line with a number but no NFR quality keyword → not in scope."""
    spec = _make_spec(
        "# Spec\n\n"
        "## Requirements\n\n"
        "- FR-001: The system shall display at most 25 results per page.\n"
    )
    assert _spec_nfr_no_unit(spec, CATALOG) == []


def test_nfr_in_fenced_block_silent() -> None:
    """NFR line with bare number inside a fenced code block → no finding."""
    spec = _make_spec(
        "# Spec\n\n"
        "## Requirements\n\n"
        "```\n"
        "- NFR-001: latency shall be under 200\n"
        "```\n"
    )
    assert _spec_nfr_no_unit(spec, CATALOG) == []


def test_latency_with_seconds_silent() -> None:
    """Latency NFR with 'seconds' unit → no finding."""
    spec = _make_spec(
        "# Spec\n\n"
        "## Requirements\n\n"
        "- NFR-001: The system shall respond within 2 seconds.\n"
    )
    assert _spec_nfr_no_unit(spec, CATALOG) == []


def test_plan_artifact_fires_on_nfr_no_unit() -> None:
    """SPEC-NFR-NO-UNIT also applies to plan artifacts."""
    plan = _make_plan(
        "# Plan\n\n"
        "## Technical Design\n\n"
        "The system shall maintain uptime of 99.5.\n"
    )
    findings = _spec_nfr_no_unit(plan, CATALOG)
    assert len(findings) == 1
    assert findings[0].pitfall_id == "SPEC-NFR-NO-UNIT"


def test_plan_with_percent_silent() -> None:
    """Plan NFR with percent unit → no finding."""
    plan = _make_plan(
        "# Plan\n\n"
        "## Technical Design\n\n"
        "The system shall maintain uptime of 99.5 percent.\n"
    )
    assert _spec_nfr_no_unit(plan, CATALOG) == []
