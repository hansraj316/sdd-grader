"""Tests for SPEC-MISSING-PII-HANDLING pitfall.

Fires when a spec.md references personal data, PII, or regulated data categories
(GDPR, CCPA, HIPAA, email addresses, phone numbers, etc.) but contains no
privacy or data-retention statement anywhere in the document.

Sources:
  - Canon Volere Legal/Regulatory NFR category
  - ISO/IEC 25010:2011 §4.2.2.5 Confidentiality
  - GDPR Article 25 (Data Protection by Design and by Default)

Distinct from PLAN-MISSING-SECURITY (infra-level auth/TLS in the deployment plan):
this check fires on data-layer privacy obligations that must appear in the spec.

Guard:
  FIRES when: (1) PII trigger vocabulary on a non-fenced, non-blockquote line AND
              (2) no privacy silence token anywhere in the document.

Silence: any of: data retention, privacy, anonymiz*, pseudonymiz*, consent,
         data minimiz*, data protection, purge, right to erasure/deletion.
"""

from __future__ import annotations

from sddgrade.adapters.base import parse_sections
from sddgrade.catalog import load_catalog
from sddgrade.engine.lint import _spec_missing_pii_handling
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


def test_gdpr_no_privacy_fires() -> None:
    """Spec mentions GDPR with no privacy statement → fires."""
    raw = (
        "## Requirements\n\n"
        "FR-001: The system shall comply with GDPR requirements for EU users.\n"
    )
    findings = _spec_missing_pii_handling(_make_spec(raw), CATALOG)
    assert findings, "Expected a finding for GDPR mention without privacy statement"
    assert "SPEC-MISSING-PII-HANDLING" in findings[0].pitfall_id


def test_pii_keyword_no_privacy_fires() -> None:
    """Spec mentions PII with no privacy statement → fires."""
    raw = (
        "## Data Model\n\n"
        "The system stores PII including names, addresses, and identifiers.\n"
    )
    findings = _spec_missing_pii_handling(_make_spec(raw), CATALOG)
    assert findings, "Expected a finding for PII mention without privacy statement"


def test_email_address_no_privacy_fires() -> None:
    """Spec mentions email address with no privacy statement → fires."""
    raw = (
        "## Requirements\n\n"
        "FR-002: The system shall collect the user's email address for notifications.\n"
    )
    findings = _spec_missing_pii_handling(_make_spec(raw), CATALOG)
    assert findings, "Expected a finding for 'email address' without privacy statement"


def test_phone_number_no_privacy_fires() -> None:
    """Spec mentions phone number with no privacy statement → fires."""
    raw = (
        "## Requirements\n\n"
        "FR-003: Users shall provide a phone number for 2FA authentication.\n"
    )
    findings = _spec_missing_pii_handling(_make_spec(raw), CATALOG)
    assert findings, "Expected a finding for 'phone number' without privacy statement"


def test_personal_data_no_privacy_fires() -> None:
    """Spec mentions 'personal data' with no privacy statement → fires."""
    raw = (
        "## Scope\n\n"
        "This system processes personal data on behalf of enterprise clients.\n"
    )
    findings = _spec_missing_pii_handling(_make_spec(raw), CATALOG)
    assert findings, "Expected a finding for 'personal data' without privacy statement"


def test_ccpa_no_privacy_fires() -> None:
    """Spec mentions CCPA with no privacy statement → fires."""
    raw = (
        "## Compliance\n\n"
        "The service must support CCPA opt-out requests from California residents.\n"
    )
    findings = _spec_missing_pii_handling(_make_spec(raw), CATALOG)
    assert findings, "Expected a finding for 'CCPA' without privacy statement"


def test_sensitive_data_no_privacy_fires() -> None:
    """Spec mentions 'sensitive data' with no privacy statement → fires."""
    raw = (
        "## Security\n\n"
        "FR-010: The API shall encrypt sensitive data at rest.\n"
    )
    findings = _spec_missing_pii_handling(_make_spec(raw), CATALOG)
    assert findings, "Expected a finding for 'sensitive data' without privacy statement"


def test_personally_identifiable_fires() -> None:
    """Spec mentions 'personally identifiable' with no privacy statement → fires."""
    raw = (
        "## Data Requirements\n\n"
        "The log pipeline must not store personally identifiable information.\n"
    )
    findings = _spec_missing_pii_handling(_make_spec(raw), CATALOG)
    assert findings, "Expected a finding for 'personally identifiable' without privacy statement"


def test_finding_anchored_at_first_pii_line() -> None:
    """Finding is anchored at the first line with PII vocabulary."""
    raw = (
        "## Overview\n"
        "\n"
        "This is a user management service.\n"
        "FR-001: The system shall store the user's email address for login.\n"
        "FR-002: Users can update their phone number in settings.\n"
    )
    findings = _spec_missing_pii_handling(_make_spec(raw), CATALOG)
    assert findings
    assert findings[0].line == 4, f"Expected line 4, got {findings[0].line}"


def test_user_profile_fires() -> None:
    """Spec mentions 'user profile' with no privacy statement → fires."""
    raw = (
        "## Requirements\n\n"
        "FR-005: The user profile shall store display name, avatar, and preferences.\n"
    )
    findings = _spec_missing_pii_handling(_make_spec(raw), CATALOG)
    assert findings, "Expected a finding for 'user profile' without privacy statement"


# ---------------------------------------------------------------------------
# SILENT cases — check must NOT trigger
# ---------------------------------------------------------------------------


def test_gdpr_with_privacy_statement_silent() -> None:
    """Spec mentions GDPR AND has 'privacy' statement → silent."""
    raw = (
        "## Requirements\n\n"
        "FR-001: The system shall comply with GDPR requirements.\n\n"
        "## Privacy and Data Handling\n\n"
        "All data is subject to our privacy policy and data minimisation rules.\n"
    )
    findings = _spec_missing_pii_handling(_make_spec(raw), CATALOG)
    assert not findings, "'privacy' token should silence the check"


def test_pii_with_data_retention_silent() -> None:
    """Spec mentions PII AND has 'data-retention' statement → silent."""
    raw = (
        "## Data Model\n\n"
        "The system handles PII including user names and addresses.\n\n"
        "NFR-P01: The data-retention period for personal records is 90 days.\n"
    )
    findings = _spec_missing_pii_handling(_make_spec(raw), CATALOG)
    assert not findings, "data-retention token should silence the check"


def test_email_with_anonymization_silent() -> None:
    """Spec mentions email address AND has 'anonymized' → silent."""
    raw = (
        "## Requirements\n\n"
        "FR-002: The system collects email addresses for account creation.\n\n"
        "NFR-P02: Email addresses shall be anonymized in analytics reports.\n"
    )
    findings = _spec_missing_pii_handling(_make_spec(raw), CATALOG)
    assert not findings, "anonymiz* token should silence the check"


def test_pii_with_pseudonymization_silent() -> None:
    """Spec mentions PII AND has 'pseudonymised' → silent."""
    raw = (
        "## Requirements\n\n"
        "FR-001: The export service processes PII records.\n\n"
        "NFR-P01: All PII shall be pseudonymised before leaving the data warehouse.\n"
    )
    findings = _spec_missing_pii_handling(_make_spec(raw), CATALOG)
    assert not findings, "pseudonymis* token should silence the check"


def test_gdpr_with_consent_silent() -> None:
    """Spec mentions GDPR AND has 'consent' → silent."""
    raw = (
        "## Requirements\n\n"
        "FR-001: The system shall support GDPR consent withdrawal.\n\n"
        "The consent mechanism is implemented via the preference centre.\n"
    )
    findings = _spec_missing_pii_handling(_make_spec(raw), CATALOG)
    assert not findings, "consent token should silence the check"


def test_gdpr_with_data_protection_silent() -> None:
    """Spec mentions GDPR AND has 'data protection' → silent."""
    raw = (
        "## Requirements\n\n"
        "FR-001: The system shall comply with GDPR.\n\n"
        "NFR-001: The system design follows data protection by design principles.\n"
    )
    findings = _spec_missing_pii_handling(_make_spec(raw), CATALOG)
    assert not findings, "data-protection token should silence the check"


def test_fenced_block_pii_silent() -> None:
    """PII vocabulary inside a fenced code block does not trigger the check."""
    raw = (
        "## Overview\n\n"
        "The system stores benign aggregate statistics.\n\n"
        "```json\n"
        '{"field": "email_address", "type": "string"}\n'
        "```\n"
    )
    findings = _spec_missing_pii_handling(_make_spec(raw), CATALOG)
    assert not findings, "Fenced block PII vocabulary should not trigger the check"


def test_blockquote_pii_silent() -> None:
    """PII vocabulary in a blockquote line is ignored (not a normative requirement)."""
    raw = (
        "## Overview\n\n"
        "> Note: The upstream service may handle email addresses.\n"
    )
    findings = _spec_missing_pii_handling(_make_spec(raw), CATALOG)
    assert not findings, "Blockquote PII vocabulary should not trigger the check"


def test_no_pii_vocabulary_silent() -> None:
    """Spec with no PII vocabulary at all → silent."""
    raw = (
        "## Requirements\n\n"
        "FR-001: The system shall process payment transactions.\n"
        "NFR-001: Throughput shall be ≥ 1000 req/s at peak load.\n"
    )
    findings = _spec_missing_pii_handling(_make_spec(raw), CATALOG)
    assert not findings, "No PII vocabulary — should not fire"


def test_plan_artifact_not_applicable() -> None:
    """The pitfall only applies to spec artifacts, not plan."""
    raw = (
        "## Deployment\n\n"
        "FR-001: The system shall handle GDPR data subject requests.\n"
    )
    findings = _spec_missing_pii_handling(_make_plan(raw), CATALOG)
    assert not findings, "SPEC-MISSING-PII-HANDLING should not fire on plan artifacts"


def test_only_one_finding_returned() -> None:
    """Multiple PII-trigger lines → only one aggregate finding at the first."""
    raw = (
        "## Requirements\n\n"
        "FR-001: The system shall comply with GDPR for EU users.\n"
        "FR-002: Users provide their email address and phone number.\n"
        "FR-003: The service stores user profiles and date of birth.\n"
    )
    findings = _spec_missing_pii_handling(_make_spec(raw), CATALOG)
    assert len(findings) == 1, "Should fire only one aggregate finding"
    assert findings[0].line == 3, (
        f"Should anchor at first offending line (3), got {findings[0].line}"
    )


def test_right_to_erasure_silences() -> None:
    """Spec mentions GDPR AND references 'right to erasure' → silent."""
    raw = (
        "## Requirements\n\n"
        "FR-001: The system shall comply with GDPR regulations.\n\n"
        "NFR-P01: Users have the right to erasure of their personal data within 30 days.\n"
    )
    findings = _spec_missing_pii_handling(_make_spec(raw), CATALOG)
    assert not findings, "'right to erasure' should silence the check"


def test_purge_silences() -> None:
    """Spec mentions personal data AND 'purge' → silent."""
    raw = (
        "## Requirements\n\n"
        "FR-001: The system processes personal data records for billing.\n\n"
        "NFR-P01: Inactive records shall be purged after 12 months.\n"
    )
    findings = _spec_missing_pii_handling(_make_spec(raw), CATALOG)
    assert not findings, "'purge' should silence the check"
