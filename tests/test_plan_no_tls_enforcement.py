"""Tests for PLAN-NO-TLS-ENFORCEMENT pitfall."""
from __future__ import annotations

import textwrap

from sddgrade.adapters.base import parse_sections
from sddgrade.catalog import load_catalog
from sddgrade.engine.lint import _plan_no_tls_enforcement
from sddgrade.model import Artifact, ArtifactType

CATALOG = load_catalog()
PITFALL_ID = "PLAN-NO-TLS-ENFORCEMENT"


def _plan(raw: str) -> Artifact:
    raw = textwrap.dedent(raw).strip()
    return Artifact(
        path="plan.md",
        type=ArtifactType.PLAN,
        feature_id="test",
        raw=raw,
        sections=parse_sections(raw),
    )


def _findings(raw: str):
    art = _plan(raw)
    return _plan_no_tls_enforcement(art, CATALOG)


# ---------------------------------------------------------------------------
# Fire cases
# ---------------------------------------------------------------------------

def test_fire_rest_api_no_tls():
    """REST API exposed, no TLS vocabulary → fires."""
    md = """\
    ## Deployment

    Deploy the service to the production environment.
    The service exposes a REST API on port 8080.
    Authentication is handled via JWT bearer tokens.
    """
    assert _findings(md), "Should fire: REST API with no TLS"


def test_fire_graphql_no_tls():
    """GraphQL endpoint present, no TLS vocabulary → fires."""
    md = """\
    ## Release Process

    Deploy to production.
    The backend exposes a GraphQL API for the frontend clients.
    """
    assert _findings(md), "Should fire: GraphQL API with no TLS"


def test_fire_grpc_service_no_tls():
    """gRPC service present, no TLS vocabulary → fires."""
    md = """\
    ## Deployment Steps

    Deploy microservices to the staging environment.
    The order-service exposes a gRPC service on port 9090.
    """
    assert _findings(md), "Should fire: gRPC service with no TLS"


def test_fire_webhook_no_tls():
    """Webhook present, no TLS vocabulary → fires."""
    md = """\
    ## Deployment

    Release to production.
    Register a webhook with the payment provider.
    """
    assert _findings(md), "Should fire: webhook with no TLS"


def test_fire_web_app_no_tls():
    """Web application present, no TLS vocabulary → fires."""
    md = """\
    ## Deployment

    Deploy the web application to the production server.
    The web app serves dashboard pages to authenticated users.
    """
    assert _findings(md), "Should fire: web app with no TLS"


def test_fire_jwt_auth_but_no_tls():
    """JWT auth present (silences PLAN-MISSING-SECURITY) but no TLS → fires."""
    md = """\
    ## Deployment

    Deploy to production environment.
    The API uses JWT bearer tokens for authentication.
    Expose the REST API endpoint on port 8080.
    """
    assert _findings(md), "Should fire: JWT present but no TLS specified"


# ---------------------------------------------------------------------------
# Silent cases
# ---------------------------------------------------------------------------

def test_silent_https_mentioned():
    """REST API but HTTPS mentioned → silent."""
    md = """\
    ## Deployment

    Deploy to production.
    The service exposes a REST API over HTTPS on port 443.
    """
    assert not _findings(md), "Should be silent: HTTPS mentioned"


def test_silent_tls_mentioned():
    """GraphQL API but TLS mentioned → silent."""
    md = """\
    ## Release

    Deploy to production environment.
    The backend exposes a GraphQL API; TLS is terminated at the load balancer.
    """
    assert not _findings(md), "Should be silent: TLS mentioned"


def test_silent_acm_certificate():
    """API present but ACM certificate mentioned → silent."""
    md = """\
    ## Deployment Steps

    Deploy to production.
    The service exposes a REST API.
    TLS is managed via an ACM certificate on the ALB.
    """
    assert not _findings(md), "Should be silent: ACM mentioned"


def test_silent_lets_encrypt():
    """Web service but Let's Encrypt mentioned → silent."""
    md = """\
    ## Deployment

    Deploy the web service to production.
    HTTPS certificates are provisioned via Let's Encrypt.
    """
    assert not _findings(md), "Should be silent: Let's Encrypt mentioned"


def test_silent_port_443():
    """API present, port 443 mentioned → silent."""
    md = """\
    ## Deployment

    Deploy to production.
    The public API listens on port 443.
    """
    assert not _findings(md), "Should be silent: port 443 mentioned"


def test_silent_no_deploy_vocab():
    """REST API mentioned but no deployment vocabulary → silent (deploy guard)."""
    md = """\
    ## Local Development

    The service exposes a REST API locally on port 3000.
    """
    assert not _findings(md), "Should be silent: no deploy vocabulary"


def test_silent_no_api_vocab():
    """Deploy vocab present but no API/web-service vocabulary → silent."""
    md = """\
    ## Deployment

    Deploy to production environment.
    Run database migrations before starting the service.
    """
    assert not _findings(md), "Should be silent: no API exposure vocabulary"


def test_silent_fenced_api():
    """API mention only inside fenced code block → trigger excluded → silent."""
    md = """\
    ## Deployment

    Deploy to production.

    ```yaml
    # REST API config
    api:
      port: 8080
    ```

    No TLS configuration needed here.
    """
    assert not _findings(md), "Should be silent: API only in fenced block"


def test_silent_ssl_mentioned():
    """API present but SSL mentioned → silent."""
    md = """\
    ## Deployment

    Deploy to production.
    The service exposes a REST API.
    SSL termination is handled by nginx.
    """
    assert not _findings(md), "Should be silent: SSL mentioned"


def test_silent_hsts():
    """Web app present but HSTS mentioned → silent."""
    md = """\
    ## Deployment

    Deploy the web application to production.
    Configure HSTS headers to enforce HTTPS.
    """
    assert not _findings(md), "Should be silent: HSTS mentioned"
