"""Tests for SPEC-NFR-SECURITY-NO-MECHANISM pitfall check.

Fires when a normative NFR- requirement line contains a bare security adjective
(secure/safe/protected/confidential/private/tamper-proof/hack-proof) with no
concrete security mechanism token (TLS/HTTPS/encryption/RBAC/MFA/auth*/etc.).
One finding per offending line.  Spec-only.
"""

from __future__ import annotations

import pytest

from sddgrade.adapters.base import parse_sections
from sddgrade.catalog import load_catalog
from sddgrade.engine.lint import _spec_nfr_security_no_mechanism
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
# FIRE cases
# ---------------------------------------------------------------------------

def test_fires_on_secure() -> None:
    """NFR line with bare 'secure' → fires."""
    spec = _make_spec(
        "# Requirements\n\n"
        "- NFR-001: The system shall be secure.\n"
    )
    findings = _spec_nfr_security_no_mechanism(spec, CATALOG)
    assert len(findings) == 1
    assert findings[0].pitfall_id == "SPEC-NFR-SECURITY-NO-MECHANISM"


def test_fires_on_safe() -> None:
    """NFR line with bare 'safe' → fires."""
    spec = _make_spec(
        "# Requirements\n\n"
        "- NFR-002: All API calls shall be safe.\n"
    )
    findings = _spec_nfr_security_no_mechanism(spec, CATALOG)
    assert len(findings) == 1


def test_fires_on_protected() -> None:
    """NFR line with bare 'protected' → fires."""
    spec = _make_spec(
        "# Requirements\n\n"
        "- NFR-003: User data shall remain protected at all times.\n"
    )
    findings = _spec_nfr_security_no_mechanism(spec, CATALOG)
    assert len(findings) == 1


def test_fires_on_confidential() -> None:
    """NFR line with bare 'confidential' → fires."""
    spec = _make_spec(
        "# Requirements\n\n"
        "- NFR-004: Patient records shall be kept confidential.\n"
    )
    findings = _spec_nfr_security_no_mechanism(spec, CATALOG)
    assert len(findings) == 1


def test_fires_on_private() -> None:
    """NFR line with bare 'private' → fires."""
    spec = _make_spec(
        "# Requirements\n\n"
        "- NFR-005: User passwords shall be private.\n"
    )
    findings = _spec_nfr_security_no_mechanism(spec, CATALOG)
    assert len(findings) == 1


def test_fires_on_tamper_proof() -> None:
    """NFR line with 'tamper-proof' → fires."""
    spec = _make_spec(
        "# Requirements\n\n"
        "- NFR-006: Audit logs shall be tamper-proof.\n"
    )
    findings = _spec_nfr_security_no_mechanism(spec, CATALOG)
    assert len(findings) == 1


def test_fires_multiple_lines() -> None:
    """Multiple offending NFR lines → one finding each."""
    spec = _make_spec(
        "# Requirements\n\n"
        "- NFR-010: The login shall be secure.\n"
        "- NFR-011: User data shall be protected.\n"
    )
    findings = _spec_nfr_security_no_mechanism(spec, CATALOG)
    assert len(findings) == 2


# ---------------------------------------------------------------------------
# SILENT cases
# ---------------------------------------------------------------------------

def test_silent_with_tls() -> None:
    """NFR line with TLS mechanism → silent."""
    spec = _make_spec(
        "# Requirements\n\n"
        "- NFR-001: All connections shall be secure using TLS 1.3.\n"
    )
    assert _spec_nfr_security_no_mechanism(spec, CATALOG) == []


def test_silent_with_encryption() -> None:
    """NFR line with encryption mechanism → silent."""
    spec = _make_spec(
        "# Requirements\n\n"
        "- NFR-002: Sensitive data shall be protected via AES-256 encryption.\n"
    )
    assert _spec_nfr_security_no_mechanism(spec, CATALOG) == []


def test_silent_with_rbac() -> None:
    """NFR line with RBAC → silent."""
    spec = _make_spec(
        "# Requirements\n\n"
        "- NFR-003: Access shall be secure and controlled via RBAC.\n"
    )
    assert _spec_nfr_security_no_mechanism(spec, CATALOG) == []


def test_silent_with_mfa() -> None:
    """NFR line with MFA → silent."""
    spec = _make_spec(
        "# Requirements\n\n"
        "- NFR-004: User logins shall be safe, requiring MFA.\n"
    )
    assert _spec_nfr_security_no_mechanism(spec, CATALOG) == []


def test_silent_with_oauth() -> None:
    """NFR line with OAuth token → silent."""
    spec = _make_spec(
        "# Requirements\n\n"
        "- NFR-005: The API shall be secure via OAuth 2.0 token authentication.\n"
    )
    assert _spec_nfr_security_no_mechanism(spec, CATALOG) == []


def test_silent_fr_line_not_nfr() -> None:
    """FR- lines (not NFR-) are not checked."""
    spec = _make_spec(
        "# Requirements\n\n"
        "- FR-001: The system shall be secure.\n"
    )
    assert _spec_nfr_security_no_mechanism(spec, CATALOG) == []


def test_silent_fenced_block() -> None:
    """NFR line inside a fenced block → silent."""
    spec = _make_spec(
        "# Requirements\n\n"
        "```\n"
        "- NFR-001: The system shall be secure.\n"
        "```\n"
    )
    assert _spec_nfr_security_no_mechanism(spec, CATALOG) == []


def test_silent_non_spec_artifact() -> None:
    """Plan artifact → check does not apply."""
    plan = Artifact(
        path="plan.md",
        type=ArtifactType.PLAN,
        raw="## Deploy\n\n- NFR-001: shall be secure\n",
        sections=parse_sections("## Deploy\n\n- NFR-001: shall be secure\n"),
    )
    assert _spec_nfr_security_no_mechanism(plan, CATALOG) == []


def test_silent_prose_no_nfr_id() -> None:
    """Prose line with 'secure' but no NFR- id → silent."""
    spec = _make_spec(
        "# Overview\n\n"
        "The system must be secure and reliable.\n"
    )
    assert _spec_nfr_security_no_mechanism(spec, CATALOG) == []


def test_silent_jwt_mechanism() -> None:
    """NFR line with JWT/HMAC → silent."""
    spec = _make_spec(
        "# Requirements\n\n"
        "- NFR-007: Session tokens shall be private, stored as HMAC-signed JWT.\n"
    )
    assert _spec_nfr_security_no_mechanism(spec, CATALOG) == []


def test_silent_https_mechanism() -> None:
    """NFR line with HTTPS → silent."""
    spec = _make_spec(
        "# Requirements\n\n"
        "- NFR-008: All communication shall be secure using HTTPS.\n"
    )
    assert _spec_nfr_security_no_mechanism(spec, CATALOG) == []
