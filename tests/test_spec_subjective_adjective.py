"""Tests for SPEC-SUBJECTIVE-ADJECTIVE pitfall (QVscribe Level-1 Clarity Rule QV-114;
ISO/IEC/IEEE 29148:2018 §5.2.5(a) Unambiguous, §5.2.5(i) Verifiable).

Fires when a normative requirement line (shall/must or FR-/NFR- identifier) contains
an unmeasurable subjective quality adjective without a numeric measurable bound.

Adjectives checked: user-friendly, intuitive, seamless, easy-to-use, easy-to-understand,
easy-to-navigate, elegant, modern, robust, clean, fast, simple.

Silence: same line contains a numeric measurable comparator (digit + unit ms/s/%/rps/etc.)
or a percentile specifier (p95/p99/percentile).
"""

from __future__ import annotations

from sddgrade.adapters.base import parse_sections
from sddgrade.catalog import load_catalog
from sddgrade.engine.lint import _spec_subjective_adjective
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
PITFALL = "SPEC-SUBJECTIVE-ADJECTIVE"


# ---------------------------------------------------------------------------
# FIRE cases
# ---------------------------------------------------------------------------


def test_user_friendly_shall_fires() -> None:
    """'user-friendly' in shall-line fires."""
    raw = "## Requirements\n\nFR-001: The system shall provide a user-friendly interface.\n"
    findings = _spec_subjective_adjective(_make_spec(raw), CATALOG)
    assert len(findings) == 1
    assert findings[0].pitfall_id == PITFALL


def test_intuitive_shall_fires() -> None:
    """'intuitive' in shall-line fires."""
    raw = "## Requirements\n\nFR-002: The dashboard shall be intuitive to navigate.\n"
    findings = _spec_subjective_adjective(_make_spec(raw), CATALOG)
    assert len(findings) == 1
    assert findings[0].pitfall_id == PITFALL


def test_seamless_shall_fires() -> None:
    """'seamless' in shall-line fires."""
    raw = "## Requirements\n\nFR-003: The integration shall be seamless for end users.\n"
    findings = _spec_subjective_adjective(_make_spec(raw), CATALOG)
    assert len(findings) == 1
    assert findings[0].pitfall_id == PITFALL


def test_simple_must_fires() -> None:
    """'simple' in must-line fires."""
    raw = "## Requirements\n\nNFR-001: The setup process must be simple.\n"
    findings = _spec_subjective_adjective(_make_spec(raw), CATALOG)
    assert len(findings) == 1
    assert findings[0].pitfall_id == PITFALL


def test_elegant_fr_id_fires() -> None:
    """'elegant' on FR- line fires."""
    raw = "## Requirements\n\nFR-004: The API shall expose an elegant interface.\n"
    findings = _spec_subjective_adjective(_make_spec(raw), CATALOG)
    assert len(findings) == 1
    assert findings[0].pitfall_id == PITFALL


def test_robust_shall_fires() -> None:
    """'robust' in shall-line fires."""
    raw = "## Requirements\n\nNFR-002: The system shall be robust under load.\n"
    findings = _spec_subjective_adjective(_make_spec(raw), CATALOG)
    assert len(findings) == 1
    assert findings[0].pitfall_id == PITFALL


def test_fast_shall_no_unit_fires() -> None:
    """'fast' in shall-line with no numeric unit fires."""
    raw = "## Requirements\n\nNFR-003: The system shall provide fast responses.\n"
    findings = _spec_subjective_adjective(_make_spec(raw), CATALOG)
    assert len(findings) == 1
    assert findings[0].pitfall_id == PITFALL


def test_easy_to_use_shall_fires() -> None:
    """'easy to use' in shall-line fires."""
    raw = "## Requirements\n\nFR-005: The checkout flow shall be easy to use.\n"
    findings = _spec_subjective_adjective(_make_spec(raw), CATALOG)
    assert len(findings) == 1
    assert findings[0].pitfall_id == PITFALL


def test_modern_nfr_id_fires() -> None:
    """'modern' on NFR- line fires."""
    raw = "## Requirements\n\nNFR-010: The UI shall use a modern design language.\n"
    findings = _spec_subjective_adjective(_make_spec(raw), CATALOG)
    assert len(findings) == 1
    assert findings[0].pitfall_id == PITFALL


def test_multiple_adjective_lines_one_aggregate_finding() -> None:
    """Multiple adjective-bearing lines produce exactly one aggregate finding anchored at first."""
    raw = (
        "## Requirements\n\n"
        "FR-001: The UI shall be intuitive.\n"
        "FR-002: The API shall be user-friendly.\n"
        "FR-003: The setup shall be simple.\n"
    )
    findings = _spec_subjective_adjective(_make_spec(raw), CATALOG)
    assert len(findings) == 1
    assert findings[0].pitfall_id == PITFALL
    assert findings[0].line == 3  # 1-indexed: "FR-001..." is line 3


# ---------------------------------------------------------------------------
# SILENT cases
# ---------------------------------------------------------------------------


def test_silent_on_plan_artifact() -> None:
    """Does not fire on plan artifacts."""
    raw = "## Deployment\n\nDeploy a simple service to production.\n"
    findings = _spec_subjective_adjective(_make_plan(raw), CATALOG)
    assert findings == []


def test_silent_fenced_code_block() -> None:
    """Adjective inside fenced block is not flagged."""
    raw = (
        "## Requirements\n\n"
        "```\n"
        "FR-001: The system shall be user-friendly.\n"
        "```\n"
    )
    findings = _spec_subjective_adjective(_make_spec(raw), CATALOG)
    assert findings == []


def test_silent_numeric_ms_present() -> None:
    """Adjective silenced when same line has numeric ms unit (measurable bound)."""
    raw = "## Requirements\n\nNFR-001: The system shall provide fast responses in ≤ 200 ms.\n"
    findings = _spec_subjective_adjective(_make_spec(raw), CATALOG)
    assert findings == []


def test_silent_percentile_present() -> None:
    """Adjective silenced when same line has percentile specifier."""
    raw = "## Requirements\n\nNFR-002: The system shall have robust p99 latency ≤ 500 ms.\n"
    findings = _spec_subjective_adjective(_make_spec(raw), CATALOG)
    assert findings == []


def test_silent_prose_section_no_modal() -> None:
    """Adjective in non-requirement prose section doesn't fire."""
    raw = (
        "## Background\n\n"
        "We want a user-friendly product that is intuitive.\n"
    )
    findings = _spec_subjective_adjective(_make_spec(raw), CATALOG)
    assert findings == []


def test_silent_no_normative_modal_or_id() -> None:
    """Adjective in a line without any requirement indicator (no shall/must/should/FR-/NFR-) doesn't fire."""
    raw = (
        "## Design Notes\n\n"
        "The interface aims to feel seamless and clean for end users.\n"
    )
    findings = _spec_subjective_adjective(_make_spec(raw), CATALOG)
    assert findings == []


def test_silent_no_subjective_adjective() -> None:
    """Clean normative requirement with no subjective adjective doesn't fire."""
    raw = (
        "## Requirements\n\n"
        "FR-001: The system shall process requests within 200 ms (p95) at 500 concurrent users.\n"
        "NFR-001: The service shall achieve 99.9% uptime per calendar month.\n"
    )
    findings = _spec_subjective_adjective(_make_spec(raw), CATALOG)
    assert findings == []


def test_silent_fast_with_rps_unit() -> None:
    """'fast' silenced when numeric rps bound appears on same line."""
    raw = "## Requirements\n\nNFR-003: The system shall be fast (≥ 1000 rps).\n"
    findings = _spec_subjective_adjective(_make_spec(raw), CATALOG)
    assert findings == []


def test_finding_message_content() -> None:
    """Finding message mentions the pitfall id and useful guidance."""
    raw = "## Requirements\n\nFR-001: The login flow shall be intuitive.\n"
    findings = _spec_subjective_adjective(_make_spec(raw), CATALOG)
    assert len(findings) == 1
    msg = findings[0].message.lower()
    assert "subjective" in msg or "intuitive" in msg or "user-friendly" in msg
