"""Tests for SPEC-QVSCRIBE-TEMPORAL-UNBOUNDED pitfall.

The check fires when requirement-bearing lines use a temporal universal word
('always', 'never', 'at all times', 'continuously', 'at every', 'at no time',
'invariably', 'perpetually', 'without exception') that cannot be verified by
any finite test suite.

Fire cases: temporal universal on shall/must/FR-/NFR- lines in requirement sections.
Silent cases: temporal universal in prose/fenced block, no normative keyword, plan
artifact, measurable replacement, empty spec.

Source: QVscribe Continuance defect class;
        ISO/IEC/IEEE 29148:2018 §5.2.5(i) 'verifiable' characteristic.
"""

from __future__ import annotations

import pytest

from sddgrade.adapters.base import parse_sections
from sddgrade.catalog import load_catalog
from sddgrade.engine.lint import _spec_qvscribe_temporal_unbounded
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


def test_always_on_fr_line_fires() -> None:
    """FR-NNN line with 'always' in Requirements section → fires."""
    spec = _make_spec(
        "# Feature Spec\n\n"
        "## Requirements\n\n"
        "- FR-001: The system shall always be available.\n"
        "- FR-002: The system shall validate input format.\n"
    )
    findings = _spec_qvscribe_temporal_unbounded(spec, CATALOG)
    assert len(findings) == 1
    assert findings[0].pitfall_id == "SPEC-QVSCRIBE-TEMPORAL-UNBOUNDED"
    assert "temporal universal" in findings[0].message.lower()


def test_never_on_nfr_line_fires() -> None:
    """NFR-NNN line with 'never' → fires."""
    spec = _make_spec(
        "# Feature Spec\n\n"
        "## Requirements\n\n"
        "- NFR-001: The system must never lose data.\n"
    )
    findings = _spec_qvscribe_temporal_unbounded(spec, CATALOG)
    assert len(findings) == 1
    assert findings[0].pitfall_id == "SPEC-QVSCRIBE-TEMPORAL-UNBOUNDED"


def test_at_all_times_on_shall_line_fires() -> None:
    """'at all times' on a normative 'shall' line → fires."""
    spec = _make_spec(
        "# Feature Spec\n\n"
        "## Requirements\n\n"
        "- FR-001: The system shall respond at all times within SLA bounds.\n"
    )
    findings = _spec_qvscribe_temporal_unbounded(spec, CATALOG)
    assert len(findings) == 1
    assert findings[0].pitfall_id == "SPEC-QVSCRIBE-TEMPORAL-UNBOUNDED"


def test_continuously_on_fr_line_fires() -> None:
    """'continuously' on a normative FR line → fires."""
    spec = _make_spec(
        "# Feature Spec\n\n"
        "## Requirements\n\n"
        "- FR-003: The system shall continuously synchronize state across replicas.\n"
    )
    findings = _spec_qvscribe_temporal_unbounded(spec, CATALOG)
    assert len(findings) == 1


def test_invariably_on_must_line_fires() -> None:
    """'invariably' on a normative 'must' requirement line → fires."""
    spec = _make_spec(
        "# Feature Spec\n\n"
        "## Acceptance Criteria\n\n"
        "- AC-001: The authentication service must invariably return a 401 on bad credentials.\n"
    )
    findings = _spec_qvscribe_temporal_unbounded(spec, CATALOG)
    assert len(findings) == 1


def test_without_exception_on_fr_line_fires() -> None:
    """'without exception' on a normative FR line → fires."""
    spec = _make_spec(
        "# Feature Spec\n\n"
        "## Requirements\n\n"
        "- FR-010: All payments shall be encrypted without exception.\n"
    )
    findings = _spec_qvscribe_temporal_unbounded(spec, CATALOG)
    assert len(findings) == 1


def test_multiple_temporal_universals_fires_with_count() -> None:
    """Multiple temporal-universal lines → fires once with count in message."""
    spec = _make_spec(
        "# Feature Spec\n\n"
        "## Requirements\n\n"
        "- FR-001: The system shall always be available.\n"
        "- FR-002: The system must never drop a payment.\n"
        "- FR-003: The system shall handle 10k RPS at peak.\n"
    )
    findings = _spec_qvscribe_temporal_unbounded(spec, CATALOG)
    assert len(findings) == 1
    assert "2" in findings[0].message  # 2 offending lines


def test_finding_anchors_to_first_offending_line() -> None:
    """When multiple lines match, finding is anchored to the first offending line."""
    raw = (
        "# Feature\n\n"
        "## Requirements\n\n"
        "- FR-001: The system shall process payments.\n"      # line 5 — clean
        "- FR-002: The system shall always be available.\n"  # line 6 — first hit
        "- FR-003: The system must never lose data.\n"       # line 7 — second hit
    )
    spec = _make_spec(raw)
    findings = _spec_qvscribe_temporal_unbounded(spec, CATALOG)
    assert len(findings) == 1
    assert findings[0].line == 6


def test_case_insensitive_always_fires() -> None:
    """'ALWAYS' (upper case) is caught → fires."""
    spec = _make_spec(
        "# Feature Spec\n\n"
        "## Requirements\n\n"
        "- FR-001: The system shall ALWAYS maintain session integrity.\n"
    )
    findings = _spec_qvscribe_temporal_unbounded(spec, CATALOG)
    assert len(findings) == 1


# ---------------------------------------------------------------------------
# SILENT cases — check must NOT trigger
# ---------------------------------------------------------------------------


def test_measurable_threshold_silent() -> None:
    """Requirement with measurable threshold and no temporal universal → silent."""
    spec = _make_spec(
        "# Feature Spec\n\n"
        "## Requirements\n\n"
        "- FR-001: The system shall achieve 99.9% uptime per calendar month.\n"
        "- NFR-001: The system shall synchronize state within 5 seconds of any change.\n"
    )
    findings = _spec_qvscribe_temporal_unbounded(spec, CATALOG)
    assert findings == []


def test_temporal_universal_in_fenced_block_silent() -> None:
    """'always' inside a fenced code block is excluded → silent."""
    spec = _make_spec(
        "# Spec\n\n"
        "## Requirements\n\n"
        "- FR-001: The system shall process requests within 200ms.\n\n"
        "```python\n"
        "# The system shall always retry on transient errors\n"
        "retry_policy = AlwaysRetry(max=3)\n"
        "```\n"
    )
    findings = _spec_qvscribe_temporal_unbounded(spec, CATALOG)
    assert findings == []


def test_always_in_prose_overview_silent() -> None:
    """'always' in a prose Overview section with no normative keyword → silent."""
    spec = _make_spec(
        "# Feature Spec\n\n"
        "## Overview\n\n"
        "The design team is always available for consultation.\n\n"
        "## Requirements\n\n"
        "- FR-001: The system shall validate submitted forms.\n"
    )
    # Overview line: "always" appears but no shall/must/FR-/NFR- → not requirement-bearing.
    findings = _spec_qvscribe_temporal_unbounded(spec, CATALOG)
    assert findings == []


def test_never_in_plain_prose_silent() -> None:
    """'never' in a non-normative prose line → silent."""
    spec = _make_spec(
        "# Feature Spec\n\n"
        "## Background\n\n"
        "This service never existed in the legacy system.\n\n"
        "## Requirements\n\n"
        "- FR-001: The system shall export tasks as CSV.\n"
    )
    findings = _spec_qvscribe_temporal_unbounded(spec, CATALOG)
    assert findings == []


def test_non_spec_artifact_plan_silent() -> None:
    """Check does not apply to plan artifacts (artifacts=['spec'] in catalog)."""
    plan = Artifact(
        path="plan.md",
        type=ArtifactType.PLAN,
        raw=(
            "# Implementation Plan\n\n"
            "## Requirements\n\n"
            "- FR-001: The system shall always encrypt credentials at rest.\n"
        ),
        sections=parse_sections(
            "# Implementation Plan\n\n"
            "## Requirements\n\n"
            "- FR-001: The system shall always encrypt credentials at rest.\n"
        ),
    )
    findings = _spec_qvscribe_temporal_unbounded(plan, CATALOG)
    assert findings == []


def test_empty_spec_silent() -> None:
    """Empty spec produces no findings."""
    spec = _make_spec("")
    findings = _spec_qvscribe_temporal_unbounded(spec, CATALOG)
    assert findings == []


def test_pitfall_absent_from_catalog_silent() -> None:
    """When pitfall is not in catalog, check returns empty list."""
    spec = _make_spec(
        "## Requirements\n\n"
        "- FR-001: The system shall always validate tokens.\n"
    )
    findings = _spec_qvscribe_temporal_unbounded(spec, {})
    assert findings == []


def test_at_no_time_in_requirement_fires() -> None:
    """'at no time' on a normative requirement line → fires."""
    spec = _make_spec(
        "# Feature Spec\n\n"
        "## Requirements\n\n"
        "- FR-005: The system must at no time expose raw credentials in logs.\n"
    )
    findings = _spec_qvscribe_temporal_unbounded(spec, CATALOG)
    assert len(findings) == 1


def test_perpetually_in_requirement_fires() -> None:
    """'perpetually' on a normative requirement line → fires."""
    spec = _make_spec(
        "# Feature Spec\n\n"
        "## Requirements\n\n"
        "- NFR-007: The backup daemon shall perpetually run in the background.\n"
    )
    findings = _spec_qvscribe_temporal_unbounded(spec, CATALOG)
    assert len(findings) == 1


def test_continuously_in_fenced_block_silent() -> None:
    """'continuously' in a fenced block is not flagged → silent."""
    spec = _make_spec(
        "# Feature Spec\n\n"
        "## Requirements\n\n"
        "- FR-001: The system shall poll the upstream service every 30 seconds.\n\n"
        "```\n"
        "# The service shall continuously monitor the queue\n"
        "poll_interval_sec = 30\n"
        "```\n"
    )
    findings = _spec_qvscribe_temporal_unbounded(spec, CATALOG)
    assert findings == []


def test_spec_with_no_requirements_section_and_temporal_word_silent() -> None:
    """Spec with temporal word in non-requirement prose, no formal req sections → silent."""
    spec = _make_spec(
        "# Feature Spec\n\n"
        "## Design Notes\n\n"
        "The system has always been designed for high availability.\n\n"
        "## Implementation\n\n"
        "Use a load balancer to distribute traffic.\n"
    )
    # No 'shall/must/FR-/NFR-' anywhere → no requirement-bearing lines → silent
    findings = _spec_qvscribe_temporal_unbounded(spec, CATALOG)
    assert findings == []
