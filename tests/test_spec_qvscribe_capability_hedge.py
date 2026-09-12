"""Tests for SPEC-QVSCRIBE-CAPABILITY-HEDGE pitfall.

The check fires when requirement-bearing lines use capability-hedging phrases —
'shall be capable of', 'shall be allowed to', 'shall be permitted to',
'shall be designed to', 'shall be intended to', 'shall be expected to' —
instead of the direct mandatory form 'shall <verb>'.

These phrases dilute the mandatory obligation to a latent capability or design
intent.  Companion to SPEC-QVSCRIBE-SHALL-BE-ABLE-TO, covering additional
hedging forms not matched by 'shall be able to'.

Fire cases   : each hedging phrase on a requirement-bearing line.
Silent cases : direct 'shall <verb>', fenced block, non-requirement prose,
               'shall be able to' (covered by sibling check), plan artifact,
               empty spec.

Source: QVscribe Level-1 Capability/Optionality defect (QV-103 extension);
        IBM RQA Obligation Level;
        ISO/IEC/IEEE 29148:2018 §5.2.5(i) 'verifiable' characteristic.
"""

from __future__ import annotations

import pytest

from sddgrade.adapters.base import parse_sections
from sddgrade.catalog import load_catalog
from sddgrade.engine.lint import _spec_qvscribe_capability_hedge
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


def test_shall_be_capable_of_fires() -> None:
    """'shall be capable of' on FR line → fires."""
    spec = _make_spec(
        "# Feature Spec\n\n"
        "## Requirements\n\n"
        "- FR-001: The system shall be capable of handling 10,000 concurrent requests.\n"
        "- FR-002: The system shall validate input format.\n"
    )
    findings = _spec_qvscribe_capability_hedge(spec, CATALOG)
    assert len(findings) == 1
    assert findings[0].pitfall_id == "SPEC-QVSCRIBE-CAPABILITY-HEDGE"
    assert "capability-hedging" in findings[0].message.lower()


def test_shall_be_allowed_to_fires() -> None:
    """'shall be allowed to' on NFR line → fires."""
    spec = _make_spec(
        "# Feature Spec\n\n"
        "## Requirements\n\n"
        "- NFR-001: The system shall be allowed to cache responses for up to 60 seconds.\n"
    )
    findings = _spec_qvscribe_capability_hedge(spec, CATALOG)
    assert len(findings) == 1
    assert findings[0].pitfall_id == "SPEC-QVSCRIBE-CAPABILITY-HEDGE"


def test_shall_be_permitted_to_fires() -> None:
    """'shall be permitted to' on a normative line → fires."""
    spec = _make_spec(
        "# Feature Spec\n\n"
        "## Acceptance Criteria\n\n"
        "- AC-001: Users shall be permitted to export their data in CSV format.\n"
    )
    findings = _spec_qvscribe_capability_hedge(spec, CATALOG)
    assert len(findings) == 1


def test_shall_be_designed_to_fires() -> None:
    """'shall be designed to' on an FR line → fires."""
    spec = _make_spec(
        "# Auth Spec\n\n"
        "## Requirements\n\n"
        "- FR-010: The authentication module shall be designed to support OAuth 2.0.\n"
    )
    findings = _spec_qvscribe_capability_hedge(spec, CATALOG)
    assert len(findings) == 1


def test_shall_be_intended_to_fires() -> None:
    """'shall be intended to' on a normative requirement line → fires."""
    spec = _make_spec(
        "# Spec\n\n"
        "## Requirements\n\n"
        "- FR-003: The caching layer shall be intended to reduce database load by 80%.\n"
    )
    findings = _spec_qvscribe_capability_hedge(spec, CATALOG)
    assert len(findings) == 1


def test_shall_be_expected_to_fires() -> None:
    """'shall be expected to' on a normative requirement line → fires."""
    spec = _make_spec(
        "# Spec\n\n"
        "## Requirements\n\n"
        "- FR-005: The API gateway shall be expected to handle retry logic transparently.\n"
    )
    findings = _spec_qvscribe_capability_hedge(spec, CATALOG)
    assert len(findings) == 1


def test_multiple_hedging_phrases_fires_once_with_count() -> None:
    """Multiple hedging phrases → fires once with the count in the message."""
    spec = _make_spec(
        "# Feature Spec\n\n"
        "## Requirements\n\n"
        "- FR-001: The system shall be capable of handling concurrent users.\n"
        "- FR-002: The module shall be designed to support TLS 1.3.\n"
        "- FR-003: The system shall store user preferences securely.\n"  # clean
    )
    findings = _spec_qvscribe_capability_hedge(spec, CATALOG)
    assert len(findings) == 1
    assert "2" in findings[0].message  # 2 offending occurrences


def test_case_insensitive_match_fires() -> None:
    """'Shall Be Capable Of' (mixed case) is caught → fires."""
    spec = _make_spec(
        "# Feature Spec\n\n"
        "## Requirements\n\n"
        "- FR-001: The system Shall Be Capable Of recovering from a failed transaction.\n"
    )
    findings = _spec_qvscribe_capability_hedge(spec, CATALOG)
    assert len(findings) == 1


def test_finding_anchors_to_first_offending_line() -> None:
    """When multiple lines match, the finding anchors to the first one."""
    raw = (
        "# Feature\n\n"
        "## Requirements\n\n"
        "- FR-001: The system shall process payments.\n"                            # line 5 — clean
        "- FR-002: The system shall be capable of handling 5k RPS.\n"              # line 6 — first hit
        "- FR-003: The module shall be designed to scale horizontally.\n"           # line 7 — second hit
    )
    spec = _make_spec(raw)
    findings = _spec_qvscribe_capability_hedge(spec, CATALOG)
    assert len(findings) == 1
    assert findings[0].line == 6


# ---------------------------------------------------------------------------
# SILENT cases — check must NOT trigger
# ---------------------------------------------------------------------------


def test_direct_shall_verb_form_silent() -> None:
    """Direct 'shall <verb>' form with no hedging phrase → silent."""
    spec = _make_spec(
        "# Feature Spec\n\n"
        "## Requirements\n\n"
        "- FR-001: The system shall handle 10,000 concurrent requests under peak load.\n"
        "- FR-002: The system shall export user data in CSV format.\n"
    )
    findings = _spec_qvscribe_capability_hedge(spec, CATALOG)
    assert findings == []


def test_shall_be_able_to_not_caught_by_this_check() -> None:
    """'shall be able to' is covered by SPEC-QVSCRIBE-SHALL-BE-ABLE-TO, not this check."""
    spec = _make_spec(
        "# Feature Spec\n\n"
        "## Requirements\n\n"
        "- FR-001: The system shall be able to handle failover.\n"
    )
    findings = _spec_qvscribe_capability_hedge(spec, CATALOG)
    assert findings == []


def test_hedging_phrase_in_fenced_block_silent() -> None:
    """Hedging phrase inside a fenced code block is excluded → silent."""
    spec = _make_spec(
        "# Spec\n\n"
        "## Requirements\n\n"
        "- FR-001: The system shall process requests.\n\n"
        "```\n"
        "# The system shall be capable of handling retries\n"
        "retry_count = 3\n"
        "```\n"
    )
    findings = _spec_qvscribe_capability_hedge(spec, CATALOG)
    assert findings == []


def test_non_spec_artifact_type_silent() -> None:
    """Check does not apply to plan artifacts (artifacts=['spec'] in catalog)."""
    plan = Artifact(
        path="plan.md",
        type=ArtifactType.PLAN,
        raw=(
            "# Implementation Plan\n\n"
            "## Requirements\n\n"
            "- FR-001: The system shall be capable of handling failover.\n"
        ),
        sections=parse_sections(
            "# Implementation Plan\n\n"
            "## Requirements\n\n"
            "- FR-001: The system shall be capable of handling failover.\n"
        ),
    )
    findings = _spec_qvscribe_capability_hedge(plan, CATALOG)
    assert findings == []


def test_empty_spec_silent() -> None:
    """Empty spec produces no findings."""
    spec = _make_spec("")
    findings = _spec_qvscribe_capability_hedge(spec, CATALOG)
    assert findings == []


def test_pitfall_absent_from_catalog_silent() -> None:
    """When pitfall is not in catalog, check returns empty list."""
    spec = _make_spec(
        "## Requirements\n\n"
        "- FR-001: The system shall be capable of exporting data.\n"
    )
    findings = _spec_qvscribe_capability_hedge(spec, {})
    assert findings == []
