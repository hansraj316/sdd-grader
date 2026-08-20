"""Tests for SPEC-EARS-TRIGGER-INVERSION pitfall.

Fires when a non-fenced requirement-bearing line (shall) places an EARS trigger
keyword (when/while/if/where) after the normative modal instead of before it.
Correct EARS form: "When X, the system shall Y."
Inverted (defect): "The system shall Y, when X."

Scoped to requirement-bearing lines via _requirement_mask(); fenced blocks excluded.
One aggregate finding anchored at the first offending line.

Sources:
  - EARS (Easy Approach to Requirements Syntax), Mavin et al. 2009
  - ISO/IEC/IEEE 29148:2018 — EARS templates (trigger before modal)
"""

from __future__ import annotations

import pytest

from sddgrade.adapters.base import parse_sections
from sddgrade.catalog import load_catalog
from sddgrade.engine.lint import _spec_ears_trigger_inversion
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


def test_shall_when_inverted_ordering_fires() -> None:
    """'shall … when' on a requirement line → fires (trigger after modal)."""
    spec = _make_spec(
        "# Feature Spec\n\n"
        "## Requirements\n\n"
        "- FR-001: The system shall respond, when the user submits the form, within 200 ms.\n"
        "- FR-002: The system shall validate the submitted form.\n"
    )
    findings = _spec_ears_trigger_inversion(spec, CATALOG)
    assert len(findings) == 1
    assert findings[0].pitfall_id == "SPEC-EARS-TRIGGER-INVERSION"
    assert "1 requirement line" in findings[0].message


def test_shall_while_inverted_ordering_fires() -> None:
    """'shall … while' on a requirement line → fires."""
    spec = _make_spec(
        "# Spec\n\n"
        "## Requirements\n\n"
        "- FR-010: The gateway shall retry, while the upstream is unavailable, up to 3 times.\n"
    )
    findings = _spec_ears_trigger_inversion(spec, CATALOG)
    assert len(findings) == 1
    assert findings[0].pitfall_id == "SPEC-EARS-TRIGGER-INVERSION"


def test_shall_if_inverted_ordering_fires() -> None:
    """'shall … if' on a requirement line → fires."""
    spec = _make_spec(
        "# Spec\n\n"
        "## Requirements\n\n"
        "- FR-005: The service shall escalate the alert if the queue depth exceeds 1000.\n"
    )
    findings = _spec_ears_trigger_inversion(spec, CATALOG)
    assert len(findings) == 1
    assert findings[0].pitfall_id == "SPEC-EARS-TRIGGER-INVERSION"


def test_shall_where_inverted_ordering_fires() -> None:
    """'shall … where' on a requirement line → fires."""
    spec = _make_spec(
        "# Spec\n\n"
        "## Requirements\n\n"
        "- FR-007: The cache shall be bypassed where the content-type is binary.\n"
    )
    findings = _spec_ears_trigger_inversion(spec, CATALOG)
    assert len(findings) == 1
    assert findings[0].pitfall_id == "SPEC-EARS-TRIGGER-INVERSION"


def test_multiple_violations_produce_aggregate_finding() -> None:
    """Multiple inverted lines → single aggregate finding anchored at first offending line."""
    spec = _make_spec(
        "# Spec\n\n"
        "## Requirements\n\n"
        "- FR-001: The system shall respond, when the user submits, within 200 ms.\n"
        "- FR-002: The gateway shall retry if the upstream times out.\n"
        "- FR-003: The API shall authenticate all requests.\n"
    )
    findings = _spec_ears_trigger_inversion(spec, CATALOG)
    assert len(findings) == 1
    assert "2 requirement line" in findings[0].message
    # anchored at first offending line (line 5)
    assert findings[0].line == 5


def test_nfr_line_with_shall_when_fires() -> None:
    """NFR- labelled requirement line with inverted trigger → fires."""
    spec = _make_spec(
        "# Spec\n\n"
        "## Requirements\n\n"
        "- NFR-001: The system shall achieve sub-100 ms latency, when the cache is warm.\n"
    )
    findings = _spec_ears_trigger_inversion(spec, CATALOG)
    assert len(findings) == 1
    assert findings[0].pitfall_id == "SPEC-EARS-TRIGGER-INVERSION"


def test_case_insensitive_shall_when_fires() -> None:
    """Matching is case-insensitive for 'SHALL' and 'WHEN'."""
    spec = _make_spec(
        "# Spec\n\n"
        "## Requirements\n\n"
        "- FR-003: The system SHALL cache results, WHEN the upstream responds.\n"
    )
    findings = _spec_ears_trigger_inversion(spec, CATALOG)
    assert len(findings) == 1


def test_finding_anchored_at_first_offending_line() -> None:
    """First offending line is correctly identified even with leading clean lines."""
    spec = _make_spec(
        "# Spec\n\n"
        "## Requirements\n\n"
        "- FR-001: The system shall validate all submitted forms.\n"
        "- FR-002: The system shall retry the request when the upstream is unavailable.\n"
    )
    findings = _spec_ears_trigger_inversion(spec, CATALOG)
    assert len(findings) == 1
    # FR-002 is on line 6 (1-indexed)
    assert findings[0].line == 6


# ---------------------------------------------------------------------------
# SILENT cases — check should NOT trigger
# ---------------------------------------------------------------------------


def test_correct_ears_trigger_first_is_silent() -> None:
    """Trigger keyword before 'shall' (correct EARS form) → silent."""
    spec = _make_spec(
        "# Feature Spec\n\n"
        "## Requirements\n\n"
        "- FR-001: When the user submits the form, the system shall respond within 200 ms.\n"
        "- FR-002: While the upstream is unavailable, the gateway shall queue requests.\n"
        "- FR-003: If the token is expired, the system shall return HTTP 401.\n"
    )
    findings = _spec_ears_trigger_inversion(spec, CATALOG)
    assert findings == []


def test_no_trigger_keyword_is_silent() -> None:
    """Requirements with no EARS trigger keyword → silent."""
    spec = _make_spec(
        "# Spec\n\n"
        "## Requirements\n\n"
        "- FR-001: The system shall validate all submitted forms.\n"
        "- FR-002: The API must respond within 200 ms.\n"
        "- NFR-001: The service shall support 500 concurrent users.\n"
    )
    findings = _spec_ears_trigger_inversion(spec, CATALOG)
    assert findings == []


def test_shall_in_fenced_block_is_silent() -> None:
    """Inverted trigger in a fenced code block → silent."""
    spec = _make_spec(
        "# Spec\n\n"
        "## Requirements\n\n"
        "- FR-001: The API must respond within 200 ms.\n\n"
        "```python\n"
        "# FR-002: The system shall retry when the upstream times out.\n"
        "retry_if_timeout(service)\n"
        "```\n"
    )
    findings = _spec_ears_trigger_inversion(spec, CATALOG)
    assert findings == []


def test_non_normative_prose_with_when_is_silent() -> None:
    """Prose without 'shall'/'must' containing 'when' → silent (not a requirement line)."""
    spec = _make_spec(
        "# Spec\n\n"
        "## Background\n\n"
        "The system retries the request when the upstream times out.\n\n"
        "## Requirements\n\n"
        "- FR-001: The system shall validate all submitted forms.\n"
    )
    findings = _spec_ears_trigger_inversion(spec, CATALOG)
    # No normative modal in the Background line → not a requirement-bearing line
    assert findings == []


def test_plan_artifact_is_silent() -> None:
    """Pitfall applies only to spec → plan artifact is silent."""
    plan = Artifact(
        path="plan.md",
        type=ArtifactType.PLAN,
        raw=(
            "# Plan\n\n"
            "## Steps\n\n"
            "The service shall deploy, when CI is green.\n"
        ),
        sections=parse_sections(
            "# Plan\n\n"
            "## Steps\n\n"
            "The service shall deploy, when CI is green.\n"
        ),
    )
    findings = _spec_ears_trigger_inversion(plan, CATALOG)
    assert findings == []


def test_trigger_keyword_beyond_sentence_boundary_is_silent() -> None:
    """Trigger keyword appearing after a sentence boundary (period) → silent."""
    spec = _make_spec(
        "# Spec\n\n"
        "## Requirements\n\n"
        "- FR-001: The system shall respond within 200 ms. When the cache is warm it shall "
        "return results in under 50 ms.\n"
    )
    # The period before 'When' breaks the match window since [^.;!?\n]{1,80} stops at '.'
    findings = _spec_ears_trigger_inversion(spec, CATALOG)
    assert findings == []
