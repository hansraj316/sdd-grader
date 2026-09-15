"""Tests for SPEC-REFERENCE-UNRESOLVED lint check.

Fires when a spec normative requirement line cites an external standard via
bracket notation (e.g., [RFC 7662], [ISO 27001]) but the spec has no
References or Bibliography section to define it.

Sources: QVscribe QV-201 "Incomplete Requirement"; IBM RQA external-reference
completeness; ISO/IEC/IEEE 29148:2018 §5.2.5(b).
"""
from __future__ import annotations

import pytest

from sddgrade.adapters.base import parse_sections
from sddgrade.catalog import load_catalog
from sddgrade.engine.lint import _spec_reference_unresolved
from sddgrade.model import Artifact, ArtifactType


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

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
# FIRE cases
# ---------------------------------------------------------------------------

def test_rfc_citation_no_references_section_fires() -> None:
    """Normative line citing [RFC 7662] with no References section → fires."""
    spec = _make_spec(
        "# Auth Service Spec\n\n"
        "## Requirements\n\n"
        "- FR-001: The system shall implement token introspection as per [RFC 7662].\n"
        "- FR-002: The system shall validate JWTs.\n"
        "- FR-003: The system shall support OAuth 2.0.\n"
    )
    findings = _spec_reference_unresolved(spec, CATALOG)
    assert len(findings) == 1
    assert findings[0].pitfall_id == "SPEC-REFERENCE-UNRESOLVED"
    assert "RFC" in findings[0].message or "reference" in findings[0].message.lower()


def test_iso_citation_no_references_section_fires() -> None:
    """Normative line citing [ISO 27001] with no References section → fires."""
    spec = _make_spec(
        "# Security Policy Spec\n\n"
        "## Requirements\n\n"
        "- FR-001: The system shall comply with [ISO 27001] security controls.\n"
        "- FR-002: Access control must follow [ISO 27001] Annex A.\n"
        "- FR-003: Incident response shall be documented.\n"
    )
    findings = _spec_reference_unresolved(spec, CATALOG)
    assert len(findings) == 1
    assert findings[0].pitfall_id == "SPEC-REFERENCE-UNRESOLVED"


def test_ieee_citation_no_bibliography_fires() -> None:
    """Normative line with [IEEE 802.11] and no Bibliography section → fires."""
    spec = _make_spec(
        "# Wi-Fi Module Spec\n\n"
        "## Functional Requirements\n\n"
        "- FR-001: The module shall operate in compliance with [IEEE 802.11ax].\n"
        "- FR-002: The module shall support WPA3 encryption.\n"
        "- FR-003: The module shall support 2.4 GHz and 5 GHz bands.\n"
    )
    findings = _spec_reference_unresolved(spec, CATALOG)
    assert len(findings) == 1
    assert findings[0].pitfall_id == "SPEC-REFERENCE-UNRESOLVED"


def test_nist_citation_in_nfr_no_references_fires() -> None:
    """NFR line citing [NIST 800-63] with no References section → fires."""
    spec = _make_spec(
        "# Identity Service Spec\n\n"
        "## Requirements\n\n"
        "- FR-001: The system shall authenticate users.\n"
        "- FR-002: The system shall store credentials.\n"
        "- NFR-001: Password requirements must conform to [NIST 800-63B].\n"
    )
    findings = _spec_reference_unresolved(spec, CATALOG)
    assert len(findings) == 1
    assert findings[0].pitfall_id == "SPEC-REFERENCE-UNRESOLVED"


def test_multiple_citations_fires_once_at_first_line() -> None:
    """Multiple citations on different normative lines → fires once, at first offending line."""
    spec = _make_spec(
        "# Compliance Spec\n\n"
        "## Requirements\n\n"
        "- FR-001: The system shall implement [RFC 6749] for authorization.\n"
        "- FR-002: The system shall implement [RFC 7519] for JWTs.\n"
        "- FR-003: Data storage shall comply with [ISO 27001].\n"
    )
    findings = _spec_reference_unresolved(spec, CATALOG)
    assert len(findings) == 1
    assert findings[0].pitfall_id == "SPEC-REFERENCE-UNRESOLVED"
    # Message should note multiple citations
    assert "3" in findings[0].message or "requirement" in findings[0].message.lower()


def test_owasp_citation_no_references_fires() -> None:
    """Normative line citing [OWASP Top-10] with no References section → fires."""
    spec = _make_spec(
        "# Security Spec\n\n"
        "## Requirements\n\n"
        "- FR-001: The API shall protect against [OWASP Top-10] attack categories.\n"
        "- FR-002: The API shall validate all inputs.\n"
        "- FR-003: The API shall use parameterized queries.\n"
    )
    findings = _spec_reference_unresolved(spec, CATALOG)
    assert len(findings) == 1
    assert findings[0].pitfall_id == "SPEC-REFERENCE-UNRESOLVED"


# ---------------------------------------------------------------------------
# SILENT cases
# ---------------------------------------------------------------------------

def test_citation_with_references_section_silent() -> None:
    """Spec with citation AND a ## References section → silent."""
    spec = _make_spec(
        "# Auth Service Spec\n\n"
        "## Requirements\n\n"
        "- FR-001: The system shall implement token introspection as per [RFC 7662].\n"
        "- FR-002: The system shall validate JWTs.\n"
        "- FR-003: The system shall support OAuth 2.0.\n\n"
        "## References\n\n"
        "- [RFC 7662] — M. Jones, J. Bradley, 'OAuth 2.0 Token Introspection', IETF RFC 7662.\n"
    )
    findings = _spec_reference_unresolved(spec, CATALOG)
    assert findings == []


def test_citation_with_bibliography_section_silent() -> None:
    """Spec with citation AND a ## Bibliography section → silent."""
    spec = _make_spec(
        "# Security Policy Spec\n\n"
        "## Requirements\n\n"
        "- FR-001: The system shall comply with [ISO 27001] security controls.\n"
        "- FR-002: Access control must follow [ISO 27001] Annex A.\n"
        "- FR-003: Incident response shall be documented.\n\n"
        "## Bibliography\n\n"
        "- [ISO 27001] — ISO/IEC 27001:2022 Information Security Management Systems.\n"
    )
    findings = _spec_reference_unresolved(spec, CATALOG)
    assert findings == []


def test_citation_with_normative_references_section_silent() -> None:
    """Spec with citation AND a ## Normative References section → silent."""
    spec = _make_spec(
        "# Wi-Fi Module Spec\n\n"
        "## Functional Requirements\n\n"
        "- FR-001: The module shall operate in compliance with [IEEE 802.11ax].\n"
        "- FR-002: The module shall support WPA3 encryption.\n"
        "- FR-003: The module shall support 2.4 GHz and 5 GHz bands.\n\n"
        "## Normative References\n\n"
        "- [IEEE 802.11ax] — IEEE Standard for High-Efficiency Wireless LAN.\n"
    )
    findings = _spec_reference_unresolved(spec, CATALOG)
    assert findings == []


def test_no_external_citations_silent() -> None:
    """Spec with normative requirements but no bracket citations → silent."""
    spec = _make_spec(
        "# Widget Service Spec\n\n"
        "## Requirements\n\n"
        "- FR-001: The system shall process widgets within 200 ms.\n"
        "- FR-002: The system shall store up to 10 000 widgets.\n"
        "- FR-003: The system shall support concurrent access by 50 users.\n"
    )
    findings = _spec_reference_unresolved(spec, CATALOG)
    assert findings == []


def test_citation_in_fenced_block_silent() -> None:
    """Citation inside a fenced code block on normative-looking line → silent."""
    spec = _make_spec(
        "# API Spec\n\n"
        "## Requirements\n\n"
        "- FR-001: The system shall authenticate users.\n"
        "- FR-002: The system shall log requests.\n"
        "- FR-003: The system shall emit events.\n\n"
        "## Example\n\n"
        "```\n"
        "# The system shall implement token introspection as per [RFC 7662].\n"
        "```\n"
    )
    findings = _spec_reference_unresolved(spec, CATALOG)
    assert findings == []


def test_citation_on_prose_line_only_silent() -> None:
    """Citation appears in prose (non-normative) line — no shall/must/FR-/NFR- → silent."""
    spec = _make_spec(
        "# API Spec\n\n"
        "## Background\n\n"
        "This implementation follows the OAuth 2.0 spec defined in [RFC 6749].\n\n"
        "## Requirements\n\n"
        "- FR-001: The system shall authenticate users.\n"
        "- FR-002: The system shall log all access attempts.\n"
        "- FR-003: The system shall issue refresh tokens.\n"
    )
    findings = _spec_reference_unresolved(spec, CATALOG)
    assert findings == []


def test_plan_artifact_silent() -> None:
    """Plan artifact with citation on normative line → silent (check is spec-only)."""
    plan = _make_plan(
        "# Deployment Plan\n\n"
        "## Steps\n\n"
        "- The system shall follow [NIST 800-63] guidelines during deployment.\n"
        "- The system shall use TLS 1.3 for all connections.\n"
        "- The system shall validate certificates.\n"
    )
    findings = _spec_reference_unresolved(plan, CATALOG)
    assert findings == []


def test_external_standards_section_heading_silent() -> None:
    """Spec with citation AND '## External Standards' section → silent."""
    spec = _make_spec(
        "# Compliance Spec\n\n"
        "## Requirements\n\n"
        "- FR-001: The system shall implement [RFC 6749] for authorization.\n"
        "- FR-002: The system shall store tokens.\n"
        "- FR-003: The system shall expire tokens after 1 hour.\n\n"
        "## External Standards\n\n"
        "- [RFC 6749] — IETF RFC 6749, The OAuth 2.0 Authorization Framework.\n"
    )
    findings = _spec_reference_unresolved(spec, CATALOG)
    assert findings == []
