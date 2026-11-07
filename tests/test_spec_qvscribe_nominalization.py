"""Tests for SPEC-QVSCRIBE-NOMINALIZATION pitfall.

The check fires when requirement-bearing lines use verbose nominalization
phrases ('shall provide support for', 'shall perform validation of', etc.)
instead of direct active verbs. One finding per offending line.

Source: QVscribe Level-3 Clarity; IBM RQA 'action noun' anti-pattern;
        ISO/IEC/IEEE 29148:2018 §5.2.5(a) 'clear' characteristic.
"""

from __future__ import annotations

import pytest

from sddgrade.adapters.base import parse_sections
from sddgrade.catalog import load_catalog
from sddgrade.engine.lint import _spec_qvscribe_nominalization
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


def test_shall_provide_support_for_fires() -> None:
    """'shall provide support for' nominalization on FR line → fires."""
    spec = _make_spec(
        "# Feature Spec\n\n"
        "## Requirements\n\n"
        "- FR-001: The system shall provide support for CSV uploads.\n"
        "- FR-002: The system shall validate user credentials.\n"
    )
    findings = _spec_qvscribe_nominalization(spec, CATALOG)
    assert len(findings) == 1
    assert findings[0].pitfall_id == "SPEC-QVSCRIBE-NOMINALIZATION"
    assert findings[0].line == 5


def test_shall_perform_validation_of_fires() -> None:
    """'shall perform validation of' on normative line → fires."""
    spec = _make_spec(
        "# Spec\n\n"
        "## Requirements\n\n"
        "- FR-003: The system shall perform validation of all submitted fields.\n"
    )
    findings = _spec_qvscribe_nominalization(spec, CATALOG)
    assert len(findings) == 1
    assert findings[0].pitfall_id == "SPEC-QVSCRIBE-NOMINALIZATION"


def test_shall_conduct_review_of_fires() -> None:
    """'shall conduct a review of' on normative line → fires."""
    spec = _make_spec(
        "# Spec\n\n"
        "## Requirements\n\n"
        "- FR-004: The system shall conduct a review of the submitted draft.\n"
    )
    findings = _spec_qvscribe_nominalization(spec, CATALOG)
    assert len(findings) == 1
    assert findings[0].pitfall_id == "SPEC-QVSCRIBE-NOMINALIZATION"


def test_shall_carry_out_testing_of_fires() -> None:
    """'shall carry out testing of' → fires."""
    spec = _make_spec(
        "# Spec\n\n"
        "## Requirements\n\n"
        "- FR-005: The pipeline shall carry out testing of all deployed artefacts.\n"
    )
    findings = _spec_qvscribe_nominalization(spec, CATALOG)
    assert len(findings) == 1
    assert findings[0].pitfall_id == "SPEC-QVSCRIBE-NOMINALIZATION"


def test_shall_provide_ability_to_fires() -> None:
    """'shall provide the ability to' → fires."""
    spec = _make_spec(
        "# Spec\n\n"
        "## Requirements\n\n"
        "- FR-006: The system shall provide the ability to export reports.\n"
    )
    findings = _spec_qvscribe_nominalization(spec, CATALOG)
    assert len(findings) == 1
    assert findings[0].pitfall_id == "SPEC-QVSCRIBE-NOMINALIZATION"


def test_multiple_nominalized_lines_fires_per_line() -> None:
    """Two nominalized requirement lines → two findings."""
    spec = _make_spec(
        "# Spec\n\n"
        "## Requirements\n\n"
        "- FR-007: The service shall provide support for OAuth.\n"
        "- FR-008: The service shall perform validation of tokens.\n"
        "- FR-009: The service shall authenticate users.\n"
    )
    findings = _spec_qvscribe_nominalization(spec, CATALOG)
    assert len(findings) == 2
    assert all(f.pitfall_id == "SPEC-QVSCRIBE-NOMINALIZATION" for f in findings)


def test_case_insensitive_fires() -> None:
    """'SHALL PROVIDE SUPPORT FOR' (uppercase) → fires."""
    spec = _make_spec(
        "# Spec\n\n"
        "## Requirements\n\n"
        "- FR-010: The system SHALL PROVIDE SUPPORT FOR multiple locales.\n"
    )
    findings = _spec_qvscribe_nominalization(spec, CATALOG)
    assert len(findings) == 1


# ---------------------------------------------------------------------------
# SILENT cases — check must NOT trigger
# ---------------------------------------------------------------------------


def test_direct_verb_silent() -> None:
    """Well-formed spec using direct active verbs → silent."""
    spec = _make_spec(
        "# Spec\n\n"
        "## Requirements\n\n"
        "- FR-001: The system shall support CSV uploads.\n"
        "- FR-002: The system shall validate user credentials.\n"
        "- FR-003: The service shall authenticate all API requests.\n"
    )
    findings = _spec_qvscribe_nominalization(spec, CATALOG)
    assert findings == []


def test_nominalization_in_prose_silent() -> None:
    """Nominalization in a non-requirement prose paragraph → silent."""
    spec = _make_spec(
        "# Spec\n\n"
        "## Overview\n\n"
        "The goal is to provide support for multi-language content in future phases.\n\n"
        "## Requirements\n\n"
        "- FR-001: The system shall translate content on request.\n"
    )
    findings = _spec_qvscribe_nominalization(spec, CATALOG)
    assert findings == []


def test_nominalization_in_fenced_code_block_silent() -> None:
    """'shall provide support for' inside a fenced code block → silent."""
    spec = _make_spec(
        "# Spec\n\n"
        "## Requirements\n\n"
        "- FR-001: The system shall validate inputs.\n\n"
        "```\n"
        "# shall provide support for legacy format\n"
        "def handle(x): pass\n"
        "```\n"
    )
    findings = _spec_qvscribe_nominalization(spec, CATALOG)
    assert findings == []


def test_non_spec_artifact_type_silent() -> None:
    """Check does not apply to plan artifacts."""
    plan = Artifact(
        path="plan.md",
        type=ArtifactType.PLAN,
        raw=(
            "# Plan\n\n"
            "## Deployment\n\n"
            "The system shall provide support for rolling updates.\n"
        ),
        sections=parse_sections(
            "# Plan\n\n"
            "## Deployment\n\n"
            "The system shall provide support for rolling updates.\n"
        ),
    )
    findings = _spec_qvscribe_nominalization(plan, CATALOG)
    assert findings == []


def test_shall_make_provision_for_fires() -> None:
    """'shall make provision for' → fires."""
    spec = _make_spec(
        "# Spec\n\n"
        "## Requirements\n\n"
        "- FR-011: The system shall make provision for future plugin extensions.\n"
    )
    findings = _spec_qvscribe_nominalization(spec, CATALOG)
    assert len(findings) == 1
    assert findings[0].pitfall_id == "SPEC-QVSCRIBE-NOMINALIZATION"


def test_shall_perform_function_of_fires() -> None:
    """'shall perform the function of' → fires."""
    spec = _make_spec(
        "# Spec\n\n"
        "## Requirements\n\n"
        "- FR-012: The module shall perform the function of routing all API calls.\n"
    )
    findings = _spec_qvscribe_nominalization(spec, CATALOG)
    assert len(findings) == 1
    assert findings[0].pitfall_id == "SPEC-QVSCRIBE-NOMINALIZATION"
