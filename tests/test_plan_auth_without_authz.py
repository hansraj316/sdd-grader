"""Tests for PLAN-AUTH-WITHOUT-AUTHZ pitfall.

Fires when a plan.md with deployment vocabulary AND authentication vocabulary
(login/JWT/OAuth/session/password/credentials) has NO authorization vocabulary
(RBAC/ACL/role/permission/privilege/access-control) anywhere in the document.

Sources: OWASP API Security Top 10 2023 — API1:2023 Broken Object Level Authorization;
         OWASP ASVS 4.0 §4 (Access Control);
         NIST SP 800-162 (ABAC);
         Amazon Kiro security gate.
"""
from __future__ import annotations

import textwrap

from sddgrade.adapters.base import parse_sections
from sddgrade.catalog import load_catalog
from sddgrade.engine.lint import _plan_auth_without_authz
from sddgrade.model import Artifact, ArtifactType

CATALOG = load_catalog()
PITFALL = "PLAN-AUTH-WITHOUT-AUTHZ"


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
    return [f.pitfall_id for f in _plan_auth_without_authz(art, CATALOG)]


# ---------------------------------------------------------------------------
# Firing cases — authentication vocab present, no authorization vocab
# ---------------------------------------------------------------------------


def test_fires_jwt_no_authz():
    """Plan issues JWT tokens but has no authorization discussion."""
    art = _plan("""
        ## Deployment Plan
        Deploy the API gateway to production.
        The service issues JWT tokens upon successful login.
        Tokens are validated on every request using RS256 signature verification.
        The token expiry is set to 1 hour with a refresh flow for active sessions.
    """)
    assert PITFALL in _ids(art)


def test_fires_oauth_no_rbac():
    """Plan uses OAuth but never mentions roles or RBAC."""
    art = _plan("""
        ## Release Plan
        Deploy the authentication service to production.
        Users sign in via OAuth 2.0 with the identity provider.
        Access tokens have a 1-hour expiry and are refreshed silently.
        Token validation occurs at the API gateway using the public JWKS endpoint.
    """)
    assert PITFALL in _ids(art)


def test_fires_login_no_access_control():
    """Plan has login flow but no access-control model."""
    art = _plan("""
        ## Production Deployment
        Deploy version 3.0 to the production cluster.
        The login endpoint accepts username and password credentials.
        Sessions expire after 30 minutes of inactivity.
        Session tokens are stored in secure, HttpOnly cookies.
    """)
    assert PITFALL in _ids(art)


def test_fires_sso_no_authz():
    """Plan integrates SSO but mentions no authorization strategy."""
    art = _plan("""
        ## Deployment Plan
        Deploy the enterprise portal to production.
        Single Sign-On (SSO) integration with the corporate IdP is enabled.
        Users receive session tokens valid for 8 hours.
        Multi-factor authentication is enforced for all users.
    """)
    assert PITFALL in _ids(art)


def test_fires_api_key_no_authz():
    """Plan uses API keys with no authorization layer described."""
    art = _plan("""
        ## Release Plan
        Deploy the public API to production.
        Clients authenticate using API keys passed in the X-API-Key header.
        Keys are rotated every 90 days via the developer portal.
        Rate limiting is enforced at the gateway layer.
    """)
    assert PITFALL in _ids(art)


def test_fires_bearer_tokens_no_roles():
    """Plan issues bearer tokens but defines no role model."""
    art = _plan("""
        ## Production Deployment
        Deploy the microservices platform to production.
        All inter-service calls are secured with bearer tokens issued by the token service.
        Token validation is performed by the shared auth middleware.
        Services communicate over mutual TLS on the internal network.
    """)
    assert PITFALL in _ids(art)


def test_fires_password_no_roles():
    """Plan stores passwords with no role or privilege model."""
    art = _plan("""
        ## Deployment Plan
        Deploy the user management service to production.
        Passwords are stored using bcrypt with a cost factor of 12.
        Account lockout is enforced after 5 failed login attempts.
        The service exposes a REST API for account creation and login.
    """)
    assert PITFALL in _ids(art)


def test_fires_saml_no_authz():
    """Plan enables SAML federation but has no authorization vocabulary."""
    art = _plan("""
        ## Release Plan
        Deploy the identity service to the production environment.
        SAML 2.0 federation is configured with the enterprise identity provider.
        Assertions are validated using the IdP's X.509 certificate.
        Users are provisioned on first login via just-in-time provisioning.
    """)
    assert PITFALL in _ids(art)


# ---------------------------------------------------------------------------
# Silent cases — authorization vocabulary is present
# ---------------------------------------------------------------------------


def test_silent_rbac_present():
    """Plan mentions RBAC — silenced."""
    art = _plan("""
        ## Deployment Plan
        Deploy the admin portal to production.
        Users authenticate via JWT tokens issued on login.
        Access control uses RBAC with Admin, Editor, and Viewer roles.
        Every route is protected by the role middleware.
    """)
    assert PITFALL not in _ids(art)


def test_silent_permission_mentioned():
    """Plan describes permissions — silenced."""
    art = _plan("""
        ## Release Plan
        Deploy the file-sharing API to production.
        OAuth 2.0 is used for authentication.
        Each resource has owner, read, and write permissions enforced at the handler level.
    """)
    assert PITFALL not in _ids(art)


def test_silent_access_control_mentioned():
    """Plan has access-control vocabulary — silenced."""
    art = _plan("""
        ## Production Deployment
        Deploy the data platform to production.
        SSO integration with Okta is enabled for all users.
        Access control lists (ACL) govern which teams can read or write each dataset.
    """)
    assert PITFALL not in _ids(art)


def test_silent_least_privilege():
    """Plan mentions least-privilege principle — silenced."""
    art = _plan("""
        ## Deployment Plan
        Deploy the cloud infrastructure to production.
        Service accounts are created with least-privilege IAM policies.
        Users authenticate via SSO; roles are assigned at project level.
    """)
    assert PITFALL not in _ids(art)


def test_silent_opa_policy():
    """Plan uses OPA for policy decisions — silenced."""
    art = _plan("""
        ## Release Plan
        Deploy the API server to production.
        JWT-based authentication is enforced at the ingress.
        Authorization is handled by OPA (Open Policy Agent) sidecars on each service pod.
    """)
    assert PITFALL not in _ids(art)


def test_silent_role_based_access():
    """Plan describes role-based access — silenced."""
    art = _plan("""
        ## Production Deployment
        Deploy the healthcare portal to production.
        Session-based authentication is used for web clients.
        Role-based access restricts patient records to assigned care teams only.
    """)
    assert PITFALL not in _ids(art)


def test_silent_no_authn_vocab():
    """Plan has no authentication vocabulary — check does not fire."""
    art = _plan("""
        ## Deployment Plan
        Deploy the batch-processing service to production.
        The service reads from an SQS queue and writes results to S3.
        No user-facing endpoints are exposed; the service runs as a background job.
    """)
    assert PITFALL not in _ids(art)


def test_silent_spec_artifact():
    """PLAN-AUTH-WITHOUT-AUTHZ does not fire on spec artifacts."""
    art = _spec("""
        ## Deployment Plan
        Deploy the API to production.
        Users login via JWT tokens issued on sign-in.
        No authorization strategy is documented in this spec.
    """)
    assert PITFALL not in _ids(art)


def test_silent_no_deploy_guard():
    """Plan with authn vocab but no deploy guard vocabulary is silenced."""
    art = _plan("""
        ## Refactoring Notes
        Moved JWT parsing logic to the token module.
        Updated password hashing to use argon2id.
        This document describes only code changes with no infrastructure changes.
    """)
    assert PITFALL not in _ids(art)


def test_finding_anchored_at_authn_line():
    """Finding is anchored at the first non-fenced line with authentication vocab."""
    art = _plan("""
        ## Deployment Plan
        Deploy version 4.0 to the production cluster.
        The REST API is deployed behind an API Gateway.
        Users sign in using OAuth 2.0 with the identity provider.
        Session management uses secure, HttpOnly cookies.
    """)
    findings = _plan_auth_without_authz(art, CATALOG)
    assert findings, "Expected at least one finding"
    assert findings[0].pitfall_id == PITFALL
    # Finding is anchored at the OAuth/sign-in line, not line 1.
    assert findings[0].line is not None
    assert findings[0].line > 1


def test_silent_acl_present():
    """Plan with login and explicit ACL is silenced."""
    art = _plan("""
        ## Release Plan
        Deploy the document management system to production.
        Login via SAML SSO with the corporate identity provider.
        Document-level ACL controls read and write access for each team.
    """)
    assert PITFALL not in _ids(art)


def test_silent_privilege_mentioned():
    """Plan mentions privilege explicitly — silenced."""
    art = _plan("""
        ## Deployment Plan
        Deploy the admin console to production.
        Administrators authenticate using password and MFA.
        Privilege separation ensures admin operations require elevated credentials.
    """)
    assert PITFALL not in _ids(art)


def test_silent_fenced_authn_ignored():
    """Authentication vocab inside a fenced code block does not trigger the check."""
    art = _plan("""
        ## Deployment Plan
        Deploy the API server to production.
        The service exposes REST endpoints on port 8080.

        ```bash
        # Example: generate a JWT token for testing
        jwt_token=$(curl -s -X POST https://auth/login -d '{"user":"test","password":"x"}')
        ```

        All traffic is routed through the load balancer with TLS termination.
    """)
    assert PITFALL not in _ids(art)
