"""Tests for PLAN-MISSING-SECURITY — deployment plans missing security hardening vocabulary."""
from __future__ import annotations

import textwrap

from sddgrade.adapters.base import parse_sections
from sddgrade.catalog import load_catalog
from sddgrade.engine.lint import _plan_missing_security
from sddgrade.model import Artifact, ArtifactType

CATALOG = load_catalog()
PITFALL = "PLAN-MISSING-SECURITY"


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
    return [f.pitfall_id for f in _plan_missing_security(art, CATALOG)]


# ------------------------------------------------------------------ fires cases

def test_fires_on_deploy_section_no_security():
    """Plan has a Deployment section but no security mention."""
    art = _plan("""
        ## Deployment

        Run `kubectl apply -f manifests/api.yaml` to deploy the new image.
        Verify health endpoint returns 200.
    """)
    assert PITFALL in _ids(art)


def test_fires_on_deploy_vocab_no_security():
    """Plan uses 'deploy' keyword in prose but never mentions security."""
    art = _plan("""
        ## Steps

        1. Deploy the service to production using the CI pipeline.
        2. Verify health check endpoint returns 200.
        3. Run smoke tests.
    """)
    assert PITFALL in _ids(art)


def test_fires_on_production_vocab_no_security():
    """Plan mentions 'production' but has no security vocabulary."""
    art = _plan("""
        ## Release

        The feature will ship to production on Friday.
        Run the migration script before deploying.
    """)
    assert PITFALL in _ids(art)


def test_fires_on_ship_keyword():
    """Plan says 'shipping' but no security vocab."""
    art = _plan("""
        ## Steps

        1. Shipping to staging first, then production.
        2. Confirm rollback procedure is ready.
    """)
    assert PITFALL in _ids(art)


def test_message_content():
    """Finding message references security hardening."""
    art = _plan("""
        ## Deployment

        Deploy via helm upgrade.
    """)
    findings = _plan_missing_security(art, CATALOG)
    assert findings
    msg = findings[0].message.lower()
    assert "security" in msg or "auth" in msg or "encrypt" in msg


# ------------------------------------------------------------------ silent cases

def test_silent_on_auth_keyword():
    """Plan with 'authentication' present should not fire."""
    art = _plan("""
        ## Deployment

        Deploy to production. All endpoints require OAuth2 authentication.
    """)
    assert _ids(art) == []


def test_silent_on_tls_keyword():
    """Plan with 'TLS' present should not fire."""
    art = _plan("""
        ## Deployment

        Deploy the service. TLS terminates at the load balancer.
    """)
    assert _ids(art) == []


def test_silent_on_encrypt_keyword():
    """Plan with 'encrypt' present should not fire."""
    art = _plan("""
        ## Release

        Ship to production. All data is encrypted at rest and in transit.
    """)
    assert _ids(art) == []


def test_silent_on_secrets_keyword():
    """Plan with 'secrets' present should not fire."""
    art = _plan("""
        ## Deployment

        Deploy to staging. Secrets are managed via HashiCorp Vault.
    """)
    assert _ids(art) == []


def test_silent_on_iam_keyword():
    """Plan that mentions IAM should not fire."""
    art = _plan("""
        ## Deployment

        Ship to production. IAM roles restrict access to the S3 bucket.
    """)
    assert _ids(art) == []


def test_silent_on_rbac_keyword():
    """Plan that mentions RBAC should not fire."""
    art = _plan("""
        ## Deployment

        Deploy to production cluster. RBAC policies are applied via Helm values.
    """)
    assert _ids(art) == []


def test_silent_on_credential_keyword():
    """Plan that mentions credentials should not fire."""
    art = _plan("""
        ## Deployment

        Deploy to production. Database credentials are rotated automatically.
    """)
    assert _ids(art) == []


def test_silent_on_firewall_keyword():
    """Plan that mentions firewall should not fire."""
    art = _plan("""
        ## Release

        Ship to production. Firewall rules allow only port 443 inbound.
    """)
    assert _ids(art) == []


def test_silent_on_pure_refactor_plan():
    """Refactoring plan with no deployment vocab — guard should prevent firing."""
    art = _plan("""
        ## Steps

        1. Rename the `UserService` class to `AccountService`.
        2. Update all import references.
        3. Run unit tests to confirm nothing broke.
    """)
    assert _ids(art) == []


def test_fires_exactly_once():
    """Finding should fire at most once per artifact even with multiple deploy sections."""
    art = _plan("""
        ## Deployment to Staging

        Run `helm upgrade --install`.

        ## Deployment to Production

        Promote the staging image.
    """)
    ids = _ids(art)
    assert ids.count(PITFALL) == 1


def test_silent_on_spec_artifact():
    """Check only applies to plan.md; spec artifacts should not fire."""
    art = _spec("""
        ## Deployment

        The service will deploy to production. No security mentioned.
    """)
    assert _ids(art) == []


def test_silent_on_vault_keyword():
    """Plan that mentions vault should not fire."""
    art = _plan("""
        ## Deployment

        Deploy to production. Vault manages all service-to-service token exchange.
    """)
    assert _ids(art) == []
