"""Tests for SPEC-NFR-STATISTICAL-AMBIGUITY pitfall.

Fires when a latency/performance NFR qualifies the threshold with "average" or
"mean" instead of a percentile specifier (p95, p99, median, etc.).

Mean latency masks tail behaviour — p99 can be an order of magnitude higher
than the mean under realistic load distributions (Google SRE Book, Chapter 4).
ISO/IEC/IEEE 29148:2018 §5.2.5(a) requires requirements to be unambiguous;
§5.2.5(i) requires them to be verifiable by finite means.

Guard (all must appear on the same non-fenced requirement-bearing line):
  1. Latency/performance vocabulary: latency, response time, throughput,
     query time, processing time.
  2. Mean/average qualifier: average, mean.
  3. Normative modal: shall, must.

Silence: any percentile specifier on the same line: p95, p99, p50, pNN,
percentile, median.
"""

from __future__ import annotations

from sddgrade.adapters.base import parse_sections
from sddgrade.catalog import load_catalog
from sddgrade.engine.lint import _spec_nfr_statistical_ambiguity
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


def test_average_latency_fires() -> None:
    """'average latency shall be < 200ms' — no percentile → fires."""
    raw = (
        "## Requirements\n\n"
        "NFR-001: The API average latency shall be < 200ms.\n"
    )
    findings = _spec_nfr_statistical_ambiguity(_make_spec(raw), CATALOG)
    assert findings, "Expected a finding for average latency without percentile"
    assert "SPEC-NFR-STATISTICAL-AMBIGUITY" in findings[0].pitfall_id


def test_average_response_time_fires() -> None:
    """'average response time shall be under 2 seconds' → fires."""
    raw = (
        "## Requirements\n\n"
        "NFR-002: The system average response time shall be under 2 seconds.\n"
    )
    findings = _spec_nfr_statistical_ambiguity(_make_spec(raw), CATALOG)
    assert findings, "Expected a finding for average response time without percentile"


def test_mean_latency_shall_fires() -> None:
    """'mean latency shall be ≤ 300ms' → fires."""
    raw = (
        "## Requirements\n\n"
        "NFR-003: The mean latency shall be ≤ 300ms.\n"
    )
    findings = _spec_nfr_statistical_ambiguity(_make_spec(raw), CATALOG)
    assert findings, "Expected a finding for 'mean latency shall'"


def test_average_throughput_must_fires() -> None:
    """'average throughput must exceed 1000 rps' → fires."""
    raw = (
        "## Requirements\n\n"
        "The average throughput must exceed 1000 rps per node.\n"
    )
    findings = _spec_nfr_statistical_ambiguity(_make_spec(raw), CATALOG)
    assert findings, "Expected a finding for average throughput without percentile"


def test_average_query_time_fires() -> None:
    """'average query time shall be under 50ms' → fires."""
    raw = (
        "## Requirements\n\n"
        "NFR-005: The average query time shall be under 50ms.\n"
    )
    findings = _spec_nfr_statistical_ambiguity(_make_spec(raw), CATALOG)
    assert findings, "Expected a finding for average query time"


def test_average_response_time_with_load_still_fires() -> None:
    """'at 100 rps, average response time shall be < 200ms' — load present but no
    percentile: fires because the statistical qualifier is the problem."""
    raw = (
        "## Requirements\n\n"
        "NFR-006: At 100 rps, average response time shall be < 200ms.\n"
    )
    findings = _spec_nfr_statistical_ambiguity(_make_spec(raw), CATALOG)
    assert findings, (
        "Expected a finding: load context doesn't silence statistical ambiguity"
    )


def test_average_processing_time_fires() -> None:
    """'mean processing time shall not exceed 10ms' → fires."""
    raw = (
        "## Requirements\n\n"
        "The mean processing time shall not exceed 10ms per job.\n"
    )
    findings = _spec_nfr_statistical_ambiguity(_make_spec(raw), CATALOG)
    assert findings, "Expected a finding for mean processing time"


def test_finding_anchored_at_first_offending_line() -> None:
    """Finding is anchored at the line with the violation."""
    raw = (
        "## Requirements\n"
        "\n"
        "Some preamble.\n"
        "NFR-010: The average latency shall be below 100ms.\n"
    )
    findings = _spec_nfr_statistical_ambiguity(_make_spec(raw), CATALOG)
    assert findings
    assert findings[0].line == 4, f"Expected line 4, got {findings[0].line}"


# ---------------------------------------------------------------------------
# SILENT cases — check must NOT trigger
# ---------------------------------------------------------------------------


def test_p95_specifier_silences() -> None:
    """'p95 average response time shall be ≤ 200ms' — percentile present → silent."""
    raw = (
        "## Requirements\n\n"
        "NFR-001: The p95 average response time shall be ≤ 200ms.\n"
    )
    findings = _spec_nfr_statistical_ambiguity(_make_spec(raw), CATALOG)
    assert not findings, "p95 specifier should silence the check"


def test_p99_silences() -> None:
    """'p99 latency shall be under 300ms' — percentile present → silent."""
    raw = (
        "## Requirements\n\n"
        "NFR-002: The p99 latency shall be under 300ms at peak load.\n"
    )
    findings = _spec_nfr_statistical_ambiguity(_make_spec(raw), CATALOG)
    assert not findings, "p99 specifier should silence the check"


def test_median_silences() -> None:
    """'median response time shall be ≤ 100ms' — percentile present → silent."""
    raw = (
        "## Requirements\n\n"
        "NFR-003: The median response time shall be ≤ 100ms.\n"
    )
    findings = _spec_nfr_statistical_ambiguity(_make_spec(raw), CATALOG)
    assert not findings, "median specifier should silence the check"


def test_percentile_word_silences() -> None:
    """'99th percentile average latency shall be < 200ms' → silent."""
    raw = (
        "## Requirements\n\n"
        "The 99th percentile average latency shall be < 200ms.\n"
    )
    findings = _spec_nfr_statistical_ambiguity(_make_spec(raw), CATALOG)
    assert not findings, "percentile keyword should silence the check"


def test_no_latency_vocab_silent() -> None:
    """Line with 'average' and 'shall' but no performance vocabulary → silent."""
    raw = (
        "## Requirements\n\n"
        "NFR-001: The system shall maintain an average uptime.\n"
    )
    findings = _spec_nfr_statistical_ambiguity(_make_spec(raw), CATALOG)
    # 'uptime' is not in _LATENCY_QUALITY_RE, so this should not fire
    assert not findings, "No latency vocabulary — should not fire"


def test_no_normative_modal_silent() -> None:
    """'average latency should be < 200ms' — 'should' is not a normative modal → silent."""
    raw = (
        "## Requirements\n\n"
        "NFR-001: The average latency should be < 200ms (aspirational).\n"
    )
    findings = _spec_nfr_statistical_ambiguity(_make_spec(raw), CATALOG)
    assert not findings, "'should' is not in _NORMATIVE_MODAL_RE — should not fire"


def test_fenced_block_silent() -> None:
    """Violations inside a fenced code block are ignored."""
    raw = (
        "## Requirements\n\n"
        "```\n"
        "NFR-001: The average latency shall be < 200ms.\n"
        "```\n"
    )
    findings = _spec_nfr_statistical_ambiguity(_make_spec(raw), CATALOG)
    assert not findings, "Content inside fenced block should be ignored"


def test_plan_artifact_not_applicable() -> None:
    """The pitfall only applies to spec artifacts, not plan."""
    raw = (
        "## Deployment\n\n"
        "The average latency shall be < 200ms.\n"
    )
    findings = _spec_nfr_statistical_ambiguity(_make_plan(raw), CATALOG)
    assert not findings, "SPEC-NFR-STATISTICAL-AMBIGUITY should not fire on plan artifacts"


def test_p50_silences() -> None:
    """'p50 average response time shall be ≤ 150ms' — p50 is a percentile → silent."""
    raw = (
        "## Requirements\n\n"
        "NFR-004: p50 average response time shall be ≤ 150ms.\n"
    )
    findings = _spec_nfr_statistical_ambiguity(_make_spec(raw), CATALOG)
    assert not findings, "p50 specifier should silence the check"


def test_only_one_finding_returned() -> None:
    """Multiple offending lines → only one aggregate finding at the first."""
    raw = (
        "## Requirements\n\n"
        "NFR-001: The average latency shall be < 200ms.\n"
        "NFR-002: The mean response time shall be under 1s.\n"
    )
    findings = _spec_nfr_statistical_ambiguity(_make_spec(raw), CATALOG)
    assert len(findings) == 1, "Should fire only one aggregate finding"
    assert findings[0].line == 3, f"Should anchor at first offending line (3), got {findings[0].line}"
