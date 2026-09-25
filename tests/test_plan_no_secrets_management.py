"""Tests for PLAN-NO-SECRETS-MANAGEMENT pitfall.

Fires when a plan.md with deployment vocabulary AND secrets/credential vocabulary
has no secrets-management strategy (Vault, AWS Secrets Manager, SSM, etc.).

Sources: Twelve-Factor App Factor III (Config);
         Tessl production-readiness gate (secrets lifecycle);
         Kiro deployment gate (secrets management);
         OWASP Top 10 2021 A02 Cryptographic Failures.
"""
from __future__ import annotations

import textwrap

from sddgrade.adapters.base import parse_sections
from sddgrade.catalog import load_catalog
from sddgrade.engine.lint import _plan_no_secrets_management
from sddgrade.model import Artifact, ArtifactType

CATALOG = load_catalog()
PITFALL = "PLAN-NO-SECRETS-MANAGEMENT"


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


def _tasks(raw: str) -> Artifact:
    raw = textwrap.dedent(raw).strip()
    return Artifact(
        path="tasks.md",
        type=ArtifactType.TASKS,
        feature_id="test",
        raw=raw,
        sections=parse_sections(raw),
    )


def _ids(art: Artifact) -> list[str]:
    return [f.pitfall_id for f in _plan_no_secrets_management(art, CATALOG)]


# ---------------------------------------------------------------------------
# Firing cases — secrets vocab present, no management strategy
# ---------------------------------------------------------------------------


def test_fires_api_key_no_vault():
    """Plan mentions API key with deploy vocab but no secrets manager."""
    art = _plan("""
        ## Deployment Plan
        Deploy the payment service to production.
        The service uses an API key to authenticate with the billing provider.
        No secrets management strategy is documented.
    """)
    assert PITFALL in _ids(art)


def test_fires_password_no_env_var():
    """Plan mentions database password with no environment variable or vault."""
    art = _plan("""
        ## Release Plan
        Deploy version 2.0 to staging and then production.
        The database password is required for the migration step.
        Credentials should be kept secure at all times.
    """)
    assert PITFALL in _ids(art)


def test_fires_token_no_secrets_manager():
    """Plan mentions access token with no secrets-management strategy."""
    art = _plan("""
        ## Deployment Steps
        Deploy the notification service to AWS ECS production cluster.
        The service requires an OAuth token for the third-party SMS provider.
        Token handling is not documented in this plan.
    """)
    assert PITFALL in _ids(art)


def test_fires_credential_no_ssm():
    """Plan mentions credential with deploy vocab but no SSM or vault."""
    art = _plan("""
        ## Production Release
        Deploy the analytics service to the production Kubernetes cluster.
        Service credentials must be configured before starting the container.
        No secrets store is specified.
    """)
    assert PITFALL in _ids(art)


def test_fires_private_key_no_secrets_store():
    """Plan mentions private key with no secrets-management strategy."""
    art = _plan("""
        ## Deployment Procedure
        Release the TLS termination service to production.
        The private key for the TLS certificate must be provisioned on each node.
        No key management strategy is documented here.
    """)
    assert PITFALL in _ids(art)


def test_fires_passwd_no_vault():
    """Plan uses 'passwd' shorthand with no vault reference."""
    art = _plan("""
        ## Release Plan
        Deploy the legacy authentication service.
        The service reads the database passwd from its configuration.
        No secrets lifecycle is documented.
    """)
    assert PITFALL in _ids(art)


# ---------------------------------------------------------------------------
# Silent cases — secrets-management strategy present
# ---------------------------------------------------------------------------


def test_silent_vault_present():
    """Plan mentions Vault — silent."""
    art = _plan("""
        ## Deployment Plan
        Deploy the payment service to production.
        The API key for the billing provider is stored in HashiCorp Vault.
        The service retrieves the secret at startup via the Vault SDK.
    """)
    assert PITFALL not in _ids(art)


def test_silent_env_var_present():
    """Plan injects credentials as environment variables — silent."""
    art = _plan("""
        ## Release Plan
        Deploy version 3.0 to production ECS.
        The database password is injected as an environment variable via the
        AWS Secrets Manager integration.
    """)
    assert PITFALL not in _ids(art)


def test_silent_ssm_parameter_present():
    """Plan uses SSM Parameter Store — silent."""
    art = _plan("""
        ## Deployment Steps
        Deploy the notification service to AWS production.
        The OAuth token is stored in the SSM Parameter Store under
        /prod/notify/oauth-token and mounted at container start.
    """)
    assert PITFALL not in _ids(art)


def test_silent_no_secrets_vocab():
    """Plan with no secrets/credential vocabulary at all — silent."""
    art = _plan("""
        ## Deployment Plan
        Deploy the static site to S3 and CloudFront.
        Invalidate the CDN cache after each deployment.
        No authentication is required for the static assets.
    """)
    assert PITFALL not in _ids(art)


def test_silent_fenced_block_secrets():
    """Secrets vocab inside a fenced code block — silent."""
    art = _plan("""
        ## Deployment Plan
        Deploy the service to production using the following config.

        ```yaml
        API_KEY: "replace-with-actual"
        PASSWORD: "change-me"
        ```

        Credentials are managed via AWS Secrets Manager in production.
    """)
    assert PITFALL not in _ids(art)


def test_silent_no_deploy_guard():
    """Plan with secrets vocab but no deployment vocabulary — silent (deploy guard)."""
    art = _plan("""
        ## Architecture Notes
        The system uses an API key to call the external weather service.
        The token is generated per session for each user request.
        This document describes only the system architecture, not the rollout process.
    """)
    assert PITFALL not in _ids(art)


def test_silent_spec_artifact():
    """Spec artifact — PLAN-NO-SECRETS-MANAGEMENT never fires on specs."""
    art = _spec("""
        ## Deployment Plan
        Deploy the service to production.
        The API key for the provider is required for authentication.
        Token handling is not documented.
    """)
    assert PITFALL not in _ids(art)


def test_silent_tasks_artifact():
    """Tasks artifact — PLAN-NO-SECRETS-MANAGEMENT never fires on tasks."""
    art = _tasks("""
        ## Deployment Plan
        Deploy the service to production.
        - [ ] T001 Configure the API key [US1]
        - [ ] T002 Set the database password [US1]
    """)
    assert PITFALL not in _ids(art)


def test_silent_sealed_secrets():
    """Plan uses Kubernetes Sealed Secrets — silent."""
    art = _plan("""
        ## Release Plan
        Deploy the service to the production Kubernetes cluster.
        The database password is stored as a sealed-secrets resource
        and decrypted by the in-cluster Sealed Secrets controller.
    """)
    assert PITFALL not in _ids(art)


def test_silent_external_secrets_operator():
    """Plan uses External Secrets Operator — silent."""
    art = _plan("""
        ## Deployment Steps
        Deploy the service to production EKS.
        The API credentials are managed by the External Secrets Operator,
        which syncs secrets from AWS Secrets Manager into the cluster.
    """)
    assert PITFALL not in _ids(art)
