"""Tests for PLAN-NO-RATE-LIMITING pitfall.

Fires when a plan.md with deployment vocabulary AND API-surface vocabulary (REST/GraphQL/
gRPC/HTTP endpoint/webhook/route) has no rate-limiting, throttling, quota, or circuit-breaker
mention anywhere in the document.

Source: OWASP API Security Top 10:2023 API4 Unrestricted Resource Consumption,
        Tessl production-readiness gate, Kiro deployment checklist,
        ISO/IEC 25010:2011 §4.2.1.4 Capacity.
"""
from __future__ import annotations

import textwrap

from sddgrade.adapters.base import parse_sections
from sddgrade.catalog import load_catalog
from sddgrade.engine.lint import _plan_no_rate_limiting
from sddgrade.model import Artifact, ArtifactType

CATALOG = load_catalog()
PITFALL = "PLAN-NO-RATE-LIMITING"


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
    return [f.pitfall_id for f in _plan_no_rate_limiting(art, CATALOG)]


# ---------------------------------------------------------------------------
# Firing cases  (no silence tokens in text)
# ---------------------------------------------------------------------------

def test_fires_rest_api_no_rate_limit():
    """Plan deploys a REST API endpoint with no protection strategy mentioned."""
    art = _plan("""
        ## Deployment Plan
        We will deploy the service to production on Friday.
        The REST API will be available at /v2/search for all external clients.
        The endpoint will be open to the public without any access controls.
    """)
    assert PITFALL in _ids(art)


def test_fires_graphql_no_throttling():
    """Plan exposes a GraphQL endpoint with no protection mechanism."""
    art = _plan("""
        ## Release Plan
        Deploy to production environment.
        The GraphQL endpoint /api/graphql will be made public to all partners.
        No access management strategy is included in this plan.
    """)
    assert PITFALL in _ids(art)


def test_fires_grpc_no_quota():
    """Plan includes a gRPC service with no capacity enforcement."""
    art = _plan("""
        ## Deployment
        Production staging deploy scheduled.
        A new gRPC service will be exposed for internal consumers.
        No capacity enforcement is included in this plan.
    """)
    assert PITFALL in _ids(art)


def test_fires_webhook_no_protection():
    """Plan registers a webhook with no inbound protection strategy."""
    art = _plan("""
        ## Release Checklist
        Deploy to production.
        A webhook endpoint will be registered to receive GitHub events.
        No per-sender inbound protection is mentioned.
    """)
    assert PITFALL in _ids(art)


def test_fires_http_endpoint_no_rate_limit():
    """Plan adds an HTTP endpoint with no access control configuration."""
    art = _plan("""
        ## Deployment Plan
        Release to production.
        A new HTTP endpoint /admin/reports will be added.
        No access controls are described in this plan.
    """)
    assert PITFALL in _ids(art)


def test_fires_route_no_capacity():
    """Plan mentions a new route with no capacity management strategy."""
    art = _plan("""
        ## Release Plan
        Deploy to production on Monday.
        A new route /v3/export will be added to the gateway.
        No per-tenant capacity management is specified.
    """)
    assert PITFALL in _ids(art)


def test_fires_restful_api_no_protection():
    """Plan exposes a RESTful API without any capacity or safety mechanism."""
    art = _plan("""
        ## Deployment
        Production release.
        The RESTful API will be opened to external partners.
        No capacity or safety policy is in place.
    """)
    assert PITFALL in _ids(art)


# ---------------------------------------------------------------------------
# Silent cases
# ---------------------------------------------------------------------------

def test_silent_rate_limit_present():
    """rate-limit vocabulary silences the check."""
    art = _plan("""
        ## Deployment Plan
        Deploy to production.
        The REST API will be rate-limited to 100 requests per minute per API key.
        HTTP 429 is returned when the limit is exceeded.
    """)
    assert PITFALL not in _ids(art)


def test_silent_throttle_present():
    """throttling vocabulary silences the check."""
    art = _plan("""
        ## Release Plan
        Deploy to production.
        The GraphQL endpoint will be throttled at 500 req/s via the gateway.
    """)
    assert PITFALL not in _ids(art)


def test_silent_quota_present():
    """quota vocabulary silences the check."""
    art = _plan("""
        ## Deployment
        Deploy to production.
        A quota of 1000 requests per hour per tenant is enforced on the REST API.
    """)
    assert PITFALL not in _ids(art)


def test_silent_circuit_breaker_present():
    """circuit-breaker vocabulary silences the check."""
    art = _plan("""
        ## Deployment Plan
        Production release.
        The gRPC service uses a circuit-breaker with a 50% error-rate threshold.
    """)
    assert PITFALL not in _ids(art)


def test_silent_api_gateway_present():
    """api-gateway mention silences the check (implies throttling infrastructure)."""
    art = _plan("""
        ## Release Plan
        Deploy to production.
        The REST API is registered with the api-gateway which handles enforcement.
    """)
    assert PITFALL not in _ids(art)


def test_silent_back_pressure_present():
    """back-pressure vocabulary silences the check."""
    art = _plan("""
        ## Deployment
        Production deploy.
        The route /v2/stream uses back-pressure to avoid overloading consumers.
    """)
    assert PITFALL not in _ids(art)


def test_silent_no_deploy_vocab():
    """No deployment vocabulary — deploy guard prevents false positive."""
    art = _plan("""
        ## Overview
        The system exposes a REST API for internal use.
        The API route is /v1/data.
        This is an architecture overview, not a launch plan.
    """)
    assert PITFALL not in _ids(art)


def test_silent_no_api_vocab():
    """Deploy vocab present but no API-surface vocabulary — API guard prevents false positive."""
    art = _plan("""
        ## Deployment Plan
        Deploy the batch job to production.
        The worker reads from the queue and writes to the database.
        No HTTP surface is involved.
    """)
    assert PITFALL not in _ids(art)


def test_silent_in_fenced_block():
    """API vocabulary only inside a fenced code block — not a real plan statement."""
    art = _plan("""
        ## Deployment Plan
        Deploy to production.
        ```
        # endpoint: /v2/search
        # method: rest
        ```
        No external surface changes in this release.
    """)
    assert PITFALL not in _ids(art)


def test_silent_spec_artifact():
    """PLAN-NO-RATE-LIMITING must not fire on spec artifacts."""
    art = _spec("""
        ## Requirements
        The system shall expose a REST API endpoint at /v1/data.
        Deploy to production next sprint.
    """)
    assert PITFALL not in _ids(art)


def test_finding_line_is_api_vocab_line():
    """Finding anchored at the first API-vocabulary line, not line 1."""
    art = _plan("""
        ## Deployment Plan
        Deploy to production.
        The service has no external interfaces yet.
        The REST API at /v2/users will be publicly accessible.
        Access controls are left as a future iteration.
    """)
    findings = _plan_no_rate_limiting(art, CATALOG)
    hits = [f for f in findings if f.pitfall_id == PITFALL]
    assert hits, "Expected a finding"
    assert hits[0].line == 4, f"Expected line 4 (after strip/dedent), got {hits[0].line}"


def test_silent_ratelimit_no_hyphen():
    """'ratelimit' (no hyphen) silences the check."""
    art = _plan("""
        ## Deployment Plan
        Production deploy.
        The webhook endpoint has ratelimit enforcement via middleware.
    """)
    assert PITFALL not in _ids(art)


def test_silent_rate_underscore_limit():
    """'rate_limit' (underscore) silences the check."""
    art = _plan("""
        ## Release Plan
        Deploy to production.
        Nginx rate_limit is configured at 50 req/s for the REST API.
    """)
    assert PITFALL not in _ids(art)
