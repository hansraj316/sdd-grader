"""Tests for PLAN-MISSING-SECRET-ROTATION pitfall check.

Fires when a deployment plan mentions API keys, signing keys, JWT secrets,
OAuth client secrets, or similar static credentials with no rotation or
expiry strategy documented.

Sources: AWS Well-Architected SEC02-BP03; NIST SP 800-57 §5.6;
CIS Controls v8 Control 5.4; OWASP API Security API2:2023.
"""
from __future__ import annotations

import textwrap

from sddgrade.adapters.base import parse_sections
from sddgrade.catalog import load_catalog
from sddgrade.engine.lint import _plan_missing_secret_rotation
from sddgrade.model import Artifact, ArtifactType

CATALOG = load_catalog()
PITFALL = "PLAN-MISSING-SECRET-ROTATION"


def _plan(raw: str) -> Artifact:
    raw = textwrap.dedent(raw).strip()
    return Artifact(
        path="plan.md",
        type=ArtifactType.PLAN,
        feature_id="test",
        raw=raw,
        sections=parse_sections(raw),
    )


def _spec(raw: str) -> Artifact:
    raw = textwrap.dedent(raw).strip()
    return Artifact(
        path="spec.md",
        type=ArtifactType.SPEC,
        feature_id="test",
        raw=raw,
        sections=parse_sections(raw),
    )


def _ids(art: Artifact) -> list[str]:
    return [f.pitfall_id for f in _plan_missing_secret_rotation(art, CATALOG)]


# ---------------------------------------------------------------------------
# FIRE cases
# ---------------------------------------------------------------------------

def test_fires_api_key_no_rotation():
    """Plan uses an API key with no rotation strategy → fires."""
    art = _plan("""
        # Deployment Plan

        ## Deploy

        The service authenticates with Stripe using an API key stored in
        AWS Secrets Manager. The key is long-lived and manually configured.
    """)
    assert PITFALL in _ids(art)


def test_fires_signing_key_no_rotation():
    """Plan has a JWT signing key with no rotation mention → fires."""
    art = _plan("""
        # Deployment Plan

        ## Deploy

        JWT tokens are signed using an RS256 signing key stored in Vault.
        The signing key is generated once during initial setup.
    """)
    assert PITFALL in _ids(art)


def test_fires_client_secret_no_rotation():
    """OAuth client secret with no expiry policy → fires."""
    art = _plan("""
        # Deployment Plan

        ## Deploy

        OAuth2 authentication is used; the client secret is stored as an
        environment variable and injected at deploy time.
    """)
    assert PITFALL in _ids(art)


def test_fires_webhook_secret_no_rotation():
    """Webhook secret with no rotation strategy → fires."""
    art = _plan("""
        # Deployment Plan

        ## Deploy

        Deploy the API server to EC2.
        Incoming webhooks are validated using a webhook secret configured
        in the environment.
    """)
    assert PITFALL in _ids(art)


def test_fires_encryption_key_no_rotation():
    """Encryption key with no lifecycle management → fires."""
    art = _plan("""
        # Deployment Plan

        ## Deploy

        User PII is encrypted at rest using an encryption key stored in
        AWS KMS. The key is static and was provisioned during setup.
    """)
    assert PITFALL in _ids(art)


def test_fires_private_key_no_rotation():
    """Private key (RSA) with no rotation policy → fires."""
    art = _plan("""
        # Deployment Plan

        ## Deploy

        The service uses an RSA private key to sign JWTs.
        The private key is generated once and stored in Vault.
    """)
    assert PITFALL in _ids(art)


# ---------------------------------------------------------------------------
# NO-FIRE cases
# ---------------------------------------------------------------------------

def test_no_fire_key_rotation_mentioned():
    """Rotation explicitly mentioned → silenced."""
    art = _plan("""
        # Deployment Plan

        ## Deploy

        Stripe API key stored in AWS Secrets Manager with automatic rotation
        every 90 days via a Lambda rotation function.
    """)
    assert PITFALL not in _ids(art)


def test_no_fire_kms_key_rotation():
    """KMS key rotation configured → silenced."""
    art = _plan("""
        # Deployment Plan

        ## Deploy

        Encryption key managed by AWS KMS; KMS key rotation is enabled
        (annual automatic rotation). The signing key for JWTs uses this KMS key.
    """)
    assert PITFALL not in _ids(art)


def test_no_fire_vault_dynamic():
    """Vault dynamic secrets (short-lived) → silenced."""
    art = _plan("""
        # Deployment Plan

        ## Deploy

        Database credentials and API keys are issued by HashiCorp Vault
        dynamic secrets with a 1-hour TTL; each service instance gets
        an ephemeral credential that expires automatically.
    """)
    assert PITFALL not in _ids(art)


def test_no_fire_short_lived():
    """Short-lived credentials → silenced."""
    art = _plan("""
        # Deployment Plan

        ## Deploy

        Authentication tokens are short-lived (15 min TTL). The signing key
        is rotated quarterly via key rotation policy in GCP Secret Manager.
    """)
    assert PITFALL not in _ids(art)


def test_no_fire_credential_rotation():
    """Credential rotation policy present → silenced."""
    art = _plan("""
        # Deployment Plan

        ## Deploy

        OAuth client secret and webhook secret are subject to a credential
        rotation schedule enforced by the security team (90-day policy).
    """)
    assert PITFALL not in _ids(art)


def test_no_fire_no_secret_vocab():
    """Plan with no credential vocabulary → no finding."""
    art = _plan("""
        # Deployment Plan

        ## Deploy

        Deploy the API server to Kubernetes.
        Run database migrations before cutover.
        Enable health checks on /healthz.
    """)
    assert PITFALL not in _ids(art)


def test_no_fire_no_deploy_guard():
    """Plan with API key but no deploy vocabulary → guard prevents firing."""
    art = _plan("""
        # Feature Spec

        The service uses an API key to authenticate with the payment provider.
        No rotation policy is defined here.
    """)
    assert PITFALL not in _ids(art)


def test_no_fire_spec_artifact():
    """Check only applies to plan artifacts, not spec."""
    art = _spec("""
        # Feature Spec

        ## Deployment

        The system uses an API key and signing key with no rotation policy.
    """)
    assert PITFALL not in _ids(art)


def test_no_fire_fenced_trigger():
    """Secret vocabulary inside a fenced code block → no firing."""
    art = _plan("""
        # Deployment Plan

        ## Deploy

        Configure authentication:

        ```yaml
        api_key: ${STRIPE_API_KEY}
        signing_key: ${JWT_SIGNING_KEY}
        ```
    """)
    assert PITFALL not in _ids(art)


def test_no_fire_service_account_key_with_rotation():
    """Service account key with rotation strategy → silenced."""
    art = _plan("""
        # Deployment Plan

        ## Deploy

        The GCP service account key is rotated every 90 days using a
        Cloud Scheduler job that triggers key rotation and updates the
        secret in Secret Manager.
    """)
    assert PITFALL not in _ids(art)


def test_fires_at_first_trigger_line():
    """Finding anchors to the first trigger line."""
    art = _plan("""
        # Deployment Plan

        ## Deploy

        Provision the database cluster.
        The service uses an API key to authenticate with the payment gateway.
        JWT tokens are signed using a signing key stored in AWS Secrets Manager.
    """)
    findings = _plan_missing_secret_rotation(art, CATALOG)
    assert len(findings) == 1
    assert findings[0].line == 6
