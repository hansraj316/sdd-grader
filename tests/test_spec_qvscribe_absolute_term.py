"""Tests for SPEC-QVSCRIBE-ABSOLUTE-TERM pitfall.

Fires when normative requirement lines (shall/must or FR-/NFR- identifier) in a
Requirements/Acceptance section claim absolute perfection via:

  A) '100 %' adjacent to a quality-attribute word
     (uptime, availability, reliability, accuracy, consistency, coverage,
      fault-free, error-free, or 'complian…' prefix)
  B) 'zero' adjacent to a failure-mode word
     (downtime, errors, defects, failures, data loss, latency)
  C) adverbs 'fully'/'completely'/'perfectly' modifying a quality system term
     (operational, compliant, functional, consistent, reliable, available, accurate)

Sources:
  - QVscribe Verifiability defect (distinct from Temporal Universal)
  - ISO/IEC/IEEE 29148:2018 §5.2.5(i): requirement must be verifiable by finite means
"""

from __future__ import annotations

import pytest

from sddgrade.adapters.base import parse_sections
from sddgrade.catalog import load_catalog
from sddgrade.engine.lint import _spec_qvscribe_absolute_term
from sddgrade.model import Artifact, ArtifactType


def _make_spec(raw: str) -> Artifact:
    return Artifact(
        path="spec.md",
        type=ArtifactType.SPEC,
        raw=raw,
        sections=parse_sections(raw),
    )


CATALOG = load_catalog()


# ---------------------------------------------------------------------------
# FIRE cases — check should trigger
# ---------------------------------------------------------------------------


def test_100pct_uptime_shall_fires() -> None:
    """'100% uptime' on a SHALL requirement line → fires (Pattern A)."""
    spec = _make_spec(
        "# Spec\n\n"
        "## Requirements\n\n"
        "- NFR-001: The service shall achieve 100% uptime across all production regions.\n"
    )
    findings = _spec_qvscribe_absolute_term(spec, CATALOG)
    assert len(findings) == 1
    assert findings[0].pitfall_id == "SPEC-QVSCRIBE-ABSOLUTE-TERM"
    assert "100%" in findings[0].message or "absolute" in findings[0].message.lower()


def test_100pct_availability_must_fires() -> None:
    """'100% availability' on a MUST requirement line → fires (Pattern A)."""
    spec = _make_spec(
        "# Spec\n\n"
        "## Non-Functional Requirements\n\n"
        "- NFR-002: The API must guarantee 100% availability during business hours.\n"
    )
    findings = _spec_qvscribe_absolute_term(spec, CATALOG)
    assert len(findings) == 1
    assert findings[0].pitfall_id == "SPEC-QVSCRIBE-ABSOLUTE-TERM"


def test_zero_data_loss_fires() -> None:
    """'zero data loss' on a MUST requirement line → fires (Pattern B)."""
    spec = _make_spec(
        "# Spec\n\n"
        "## Requirements\n\n"
        "- FR-003: The system must guarantee zero data loss on any node failure.\n"
    )
    findings = _spec_qvscribe_absolute_term(spec, CATALOG)
    assert len(findings) == 1
    assert findings[0].pitfall_id == "SPEC-QVSCRIBE-ABSOLUTE-TERM"


def test_zero_errors_fires() -> None:
    """'zero errors' on a SHALL line → fires (Pattern B)."""
    spec = _make_spec(
        "# Spec\n\n"
        "## Requirements\n\n"
        "- FR-004: The export service shall produce zero errors in all transactions.\n"
    )
    findings = _spec_qvscribe_absolute_term(spec, CATALOG)
    assert len(findings) == 1


def test_fully_compliant_fires() -> None:
    """'fully compliant' on a SHALL requirement line → fires (Pattern C)."""
    spec = _make_spec(
        "# Spec\n\n"
        "## Requirements\n\n"
        "- FR-005: The system shall be fully compliant with WCAG 2.1.\n"
    )
    findings = _spec_qvscribe_absolute_term(spec, CATALOG)
    assert len(findings) == 1
    assert findings[0].pitfall_id == "SPEC-QVSCRIBE-ABSOLUTE-TERM"


def test_completely_reliable_fires() -> None:
    """'completely reliable' on a MUST requirement line → fires (Pattern C)."""
    spec = _make_spec(
        "# Spec\n\n"
        "## Requirements\n\n"
        "- NFR-006: The backup system must be completely reliable under all conditions.\n"
    )
    findings = _spec_qvscribe_absolute_term(spec, CATALOG)
    assert len(findings) == 1


def test_multiple_violations_single_aggregate_finding() -> None:
    """Two lines with absolute-term violations → single aggregate finding at first line."""
    spec = _make_spec(
        "# Spec\n\n"
        "## Requirements\n\n"
        "- NFR-001: The service shall achieve 100% uptime at all times.\n"
        "- NFR-002: The API must guarantee zero data loss on any failure.\n"
        "- FR-001: The system shall handle all submitted requests.\n"
    )
    findings = _spec_qvscribe_absolute_term(spec, CATALOG)
    assert len(findings) == 1
    assert "2 requirement line" in findings[0].message
    assert findings[0].line == 5  # first offending line (1-indexed)


# ---------------------------------------------------------------------------
# SILENT cases — check should NOT trigger
# ---------------------------------------------------------------------------


def test_bounded_threshold_is_silent() -> None:
    """99.95% uptime (bounded threshold, not 100%) → silent."""
    spec = _make_spec(
        "# Spec\n\n"
        "## Requirements\n\n"
        "- NFR-001: The service shall achieve 99.95% uptime per calendar month.\n"
        "- FR-001: The system shall handle all submitted requests.\n"
    )
    findings = _spec_qvscribe_absolute_term(spec, CATALOG)
    assert findings == []


def test_rpo_zero_without_failure_mode_word_is_silent() -> None:
    """'RPO=0' on a requirement line (no adjacent failure-mode noun) → silent."""
    spec = _make_spec(
        "# Spec\n\n"
        "## Requirements\n\n"
        "- NFR-002: The database must achieve RPO=0 for committed transactions on graceful shutdown.\n"
    )
    findings = _spec_qvscribe_absolute_term(spec, CATALOG)
    assert findings == []


def test_100pct_without_quality_attribute_is_silent() -> None:
    """'100%' on a requirement line with no adjacent quality attribute word → silent."""
    spec = _make_spec(
        "# Spec\n\n"
        "## Requirements\n\n"
        "- FR-003: The report shall display 100% of the user's tasks on the dashboard.\n"
    )
    findings = _spec_qvscribe_absolute_term(spec, CATALOG)
    assert findings == []


def test_absolute_term_in_fenced_block_is_silent() -> None:
    """'100% uptime' inside a fenced code block → silent."""
    spec = _make_spec(
        "# Spec\n\n"
        "## Requirements\n\n"
        "- NFR-001: The API must respond within 200 ms.\n\n"
        "```\n"
        "# NOTE: target is 100% uptime — design goal only, not a hard SLA\n"
        "```\n"
    )
    findings = _spec_qvscribe_absolute_term(spec, CATALOG)
    assert findings == []


def test_absolute_term_in_prose_without_modal_is_silent() -> None:
    """'100% availability' in Background prose (no shall/must, no FR-/NFR- id) → silent."""
    spec = _make_spec(
        "# Spec\n\n"
        "## Background\n\n"
        "The aspirational goal is 100% availability, but the actual SLA is 99.9% per quarter.\n\n"
        "## Requirements\n\n"
        "- FR-001: The system shall validate all submitted forms.\n"
    )
    findings = _spec_qvscribe_absolute_term(spec, CATALOG)
    assert findings == []


def test_plan_artifact_is_silent() -> None:
    """Pitfall applies only to spec artifacts → plan is silent."""
    plan = Artifact(
        path="plan.md",
        type=ArtifactType.PLAN,
        raw=(
            "# Plan\n\n"
            "## Deployment\n\n"
            "- NFR-001: The service shall achieve 100% uptime in production.\n"
        ),
        sections=parse_sections(
            "# Plan\n\n"
            "## Deployment\n\n"
            "- NFR-001: The service shall achieve 100% uptime in production.\n"
        ),
    )
    findings = _spec_qvscribe_absolute_term(plan, CATALOG)
    assert findings == []
