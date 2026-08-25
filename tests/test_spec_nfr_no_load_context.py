"""Tests for SPEC-NFR-NO-LOAD-CONTEXT pitfall.

Fires when a performance/latency NFR states a unitised time threshold
(e.g. "200ms", "2 seconds") but no load or measurement context ("at N
concurrent users", "under peak load", "p95", ...) — leaving the
threshold unverifiable in Canon Volere's fit-criterion sense: a tester
does not know at what load the threshold is expected to hold.

Guard: non-fenced line matches performance vocabulary (latency/throughput/
response time/response latency/uptime/availability) AND a normative
indicator (shall/must/should/FR-\\d/NFR-\\d) AND a digit followed by a
time-unit token (ms/second/minute/hour/day).

Silence: any load-context token on the same line — concurrent, users,
requests per second, rps/tps/qps, peak, load, p95/p99, percentile, or
"at N users/requests/concurrent".

Sources:
  - Canon Volere fit-criterion rule (Alexander & Stevens)
  - MAQA Verifiability (Level 2)
  - Complements SPEC-NFR-NO-THRESHOLD (no number) and SPEC-NFR-NO-UNIT
    (number without unit) — this is the third distinct gap.
"""

from __future__ import annotations

from sddgrade.adapters.base import parse_sections
from sddgrade.catalog import load_catalog
from sddgrade.engine.lint import _spec_nfr_no_load_context
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


def test_latency_ms_without_load_context_fires() -> None:
    """Latency NFR with 200ms threshold but no load context → fires."""
    spec = _make_spec(
        "# Spec\n\n"
        "## Requirements\n\n"
        "- NFR-001: The API shall respond within 200ms.\n"
    )
    findings = _spec_nfr_no_load_context(spec, CATALOG)
    assert len(findings) == 1
    assert findings[0].pitfall_id == "SPEC-NFR-NO-LOAD-CONTEXT"
    assert "load" in findings[0].message.lower()


def test_response_time_seconds_no_context_fires() -> None:
    """'response time' + '2 seconds' + no load context → fires."""
    spec = _make_spec(
        "# Spec\n\n"
        "## Requirements\n\n"
        "- NFR-002: The system shall have a response time of 2 seconds.\n"
    )
    findings = _spec_nfr_no_load_context(spec, CATALOG)
    assert len(findings) == 1
    assert findings[0].pitfall_id == "SPEC-NFR-NO-LOAD-CONTEXT"


def test_throughput_within_time_no_context_fires() -> None:
    """Throughput NFR with a time threshold but no load context → fires."""
    spec = _make_spec(
        "# Spec\n\n"
        "## Requirements\n\n"
        "- NFR-003: Throughput must complete a batch within 30 seconds.\n"
    )
    findings = _spec_nfr_no_load_context(spec, CATALOG)
    assert len(findings) == 1


def test_response_latency_hours_no_context_fires() -> None:
    """Response-latency NFR quantified in hours but no context → fires."""
    spec = _make_spec(
        "# Spec\n\n"
        "## Requirements\n\n"
        "- NFR-004: Response latency shall not exceed 2 hours.\n"
    )
    findings = _spec_nfr_no_load_context(spec, CATALOG)
    assert len(findings) == 1


def test_availability_time_threshold_no_context_fires() -> None:
    """Availability NFR + time threshold with no context → fires."""
    spec = _make_spec(
        "# Spec\n\n"
        "## Requirements\n\n"
        "- NFR-005: Availability recovery shall complete within 5 minutes.\n"
    )
    findings = _spec_nfr_no_load_context(spec, CATALOG)
    assert len(findings) == 1


def test_finding_anchored_to_offending_line() -> None:
    """Finding line is the offending line, not a preceding FR."""
    raw = (
        "# Spec\n\n"
        "## Requirements\n\n"
        "- FR-001: The system shall render results.\n"
        "- NFR-001: Latency shall stay below 250ms.\n"
    )
    spec = _make_spec(raw)
    findings = _spec_nfr_no_load_context(spec, CATALOG)
    assert len(findings) == 1
    assert findings[0].line == 6


def test_plan_artifact_fires() -> None:
    """Check applies to plan artifacts too."""
    plan = _make_plan(
        "# Plan\n\n"
        "## Non-Functional Requirements\n\n"
        "The service shall keep latency below 300ms.\n"
    )
    findings = _spec_nfr_no_load_context(plan, CATALOG)
    assert len(findings) == 1
    assert findings[0].pitfall_id == "SPEC-NFR-NO-LOAD-CONTEXT"


# ---------------------------------------------------------------------------
# SILENT cases — check must NOT trigger
# ---------------------------------------------------------------------------


def test_p95_load_context_silent() -> None:
    """p95 percentile counts as load context → silent."""
    spec = _make_spec(
        "# Spec\n\n"
        "## Requirements\n\n"
        "- NFR-001: The API shall respond within 200ms (p95 latency).\n"
    )
    assert _spec_nfr_no_load_context(spec, CATALOG) == []


def test_p99_load_context_silent() -> None:
    """p99 also counts as load context → silent."""
    spec = _make_spec(
        "# Spec\n\n"
        "## Requirements\n\n"
        "- NFR-002: Latency shall be under 400ms at the p99 percentile.\n"
    )
    assert _spec_nfr_no_load_context(spec, CATALOG) == []


def test_concurrent_users_load_context_silent() -> None:
    """'concurrent users' silences the check."""
    spec = _make_spec(
        "# Spec\n\n"
        "## Requirements\n\n"
        "- NFR-003: The API shall respond within 200ms at 500 concurrent users under peak load.\n"
    )
    assert _spec_nfr_no_load_context(spec, CATALOG) == []


def test_rps_load_context_silent() -> None:
    """'rps' silences the check."""
    spec = _make_spec(
        "# Spec\n\n"
        "## Requirements\n\n"
        "- NFR-004: Throughput shall stay under 2 seconds at 1000 rps.\n"
    )
    assert _spec_nfr_no_load_context(spec, CATALOG) == []


def test_peak_load_context_silent() -> None:
    """'peak load' silences the check."""
    spec = _make_spec(
        "# Spec\n\n"
        "## Requirements\n\n"
        "- NFR-005: Response time shall be below 500ms under peak load.\n"
    )
    assert _spec_nfr_no_load_context(spec, CATALOG) == []


def test_requests_per_second_load_context_silent() -> None:
    """'requests per second' silences the check."""
    spec = _make_spec(
        "# Spec\n\n"
        "## Requirements\n\n"
        "- NFR-006: Latency shall be under 100ms while handling 5000 requests per second.\n"
    )
    assert _spec_nfr_no_load_context(spec, CATALOG) == []


def test_no_time_threshold_silent() -> None:
    """Latency NFR with no digit+time-unit threshold — not our case."""
    spec = _make_spec(
        "# Spec\n\n"
        "## Requirements\n\n"
        "- NFR-001: The system shall have low latency.\n"
    )
    assert _spec_nfr_no_load_context(spec, CATALOG) == []


def test_no_performance_vocab_silent() -> None:
    """A time-threshold requirement outside latency/throughput scope → silent."""
    spec = _make_spec(
        "# Spec\n\n"
        "## Requirements\n\n"
        "- FR-001: The system shall email the user within 2 seconds of sign-up.\n"
    )
    assert _spec_nfr_no_load_context(spec, CATALOG) == []


def test_no_normative_modal_silent() -> None:
    """Line lacks a shall/must/FR-/NFR- indicator → not a normative requirement."""
    spec = _make_spec(
        "# Spec\n\n"
        "## Notes\n\n"
        "Historical latency observations averaged around 200ms.\n"
    )
    assert _spec_nfr_no_load_context(spec, CATALOG) == []


def test_line_in_fenced_block_silent() -> None:
    """Fenced code blocks are ignored — no finding on example snippet."""
    spec = _make_spec(
        "# Spec\n\n"
        "## Requirements\n\n"
        "```\n"
        "- NFR-001: latency shall be under 200ms\n"
        "```\n"
    )
    assert _spec_nfr_no_load_context(spec, CATALOG) == []


def test_only_one_finding_per_artifact() -> None:
    """Multiple offending lines → one aggregate finding."""
    raw = (
        "# Spec\n\n"
        "## Requirements\n\n"
        "- NFR-001: Latency shall be below 200ms.\n"
        "- NFR-002: Response time shall be below 500ms.\n"
        "- NFR-003: Throughput shall complete in 2 seconds.\n"
    )
    spec = _make_spec(raw)
    findings = _spec_nfr_no_load_context(spec, CATALOG)
    assert len(findings) == 1


def test_percentile_word_silences() -> None:
    """The word 'percentile' alone silences the check even without p95/p99."""
    spec = _make_spec(
        "# Spec\n\n"
        "## Requirements\n\n"
        "- NFR-001: Latency shall be under 250ms at the 95th percentile.\n"
    )
    assert _spec_nfr_no_load_context(spec, CATALOG) == []


def test_benign_lookalike_line_silent() -> None:
    """Regression: the benign-lookalike corpus line with 'p95 latency' must stay silent.

    Line: 'FR-002: The system shall keep p95 import-status latency under 500 ms
    while an import is running.' — p95 in context, must not fire.
    """
    spec = _make_spec(
        "# Spec\n\n"
        "## Requirements\n\n"
        "- FR-002: The system shall keep p95 import-status latency under 500 ms "
        "while an import is running.\n"
    )
    assert _spec_nfr_no_load_context(spec, CATALOG) == []
