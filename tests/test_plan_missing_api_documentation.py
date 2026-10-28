"""Tests for PLAN-MISSING-API-DOCUMENTATION pitfall.

Fires when a deployment plan exposes API endpoint vocabulary but has no
API documentation strategy (OpenAPI/Swagger/API spec/API reference/Redoc/etc.).

Sources: Canon Volere (documented fit criteria); Kiro production-readiness API gate;
Tessl API quality; OpenAPI Initiative; ISO/IEC 25010:2023 §4.3.3 Maintainability.
"""
from __future__ import annotations

import textwrap

from sddgrade.adapters.base import parse_sections
from sddgrade.catalog import load_catalog
from sddgrade.engine.lint import _plan_missing_api_documentation
from sddgrade.model import Artifact, ArtifactType

CATALOG = load_catalog()
PITFALL = "PLAN-MISSING-API-DOCUMENTATION"


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
    return [f.pitfall_id for f in _plan_missing_api_documentation(art, CATALOG)]


# ---------------------------------------------------------------------------
# Firing cases — API endpoint vocab present, no documentation strategy
# ---------------------------------------------------------------------------


def test_fires_rest_get_endpoint():
    """Plan exposes GET / endpoint without documentation vocabulary."""
    art = _plan("""
        # Deployment Plan

        ## Deployment

        Deploy the service to AWS ECS with Fargate.

        The service exposes GET /users and POST /users endpoints for the mobile client.
    """)
    assert _ids(art) == [PITFALL]


def test_fires_graphql_endpoint():
    """Plan exposes a GraphQL API endpoint without documentation vocabulary."""
    art = _plan("""
        # Plan

        ## Deployment

        Deploy to Kubernetes via Helm chart.

        The backend exposes a GraphQL API endpoint for the React frontend.
    """)
    assert _ids(art) == [PITFALL]


def test_fires_grpc_service():
    """Plan exposes gRPC service without documentation vocabulary."""
    art = _plan("""
        # Deployment Plan

        ## Deployment

        Release to production cluster.

        Introduce a gRPC service to handle order-processing between microservices.
    """)
    assert _ids(art) == [PITFALL]


def test_fires_webhook_endpoint():
    """Plan exposes a webhook endpoint without documentation vocabulary."""
    art = _plan("""
        # Plan

        ## Deployment

        Deploy the webhook receiver to AWS Lambda.

        The webhook endpoint accepts GitHub push events and triggers CI pipelines.
    """)
    assert _ids(art) == [PITFALL]


def test_fires_post_endpoint():
    """Plan exposes POST / endpoint without documentation vocabulary."""
    art = _plan("""
        # Deployment

        ## Deploy

        Push to production server via Ansible.

        Adds a POST /submissions endpoint that accepts JSON payloads from partners.
    """)
    assert _ids(art) == [PITFALL]


# ---------------------------------------------------------------------------
# Silent cases — documented, no deploy vocab, no endpoint vocab, fenced, heading
# ---------------------------------------------------------------------------


def test_silent_swagger_present():
    """Plan with swagger documentation should not fire."""
    art = _plan("""
        # Deployment Plan

        ## Deployment

        Deploy to AWS ECS.

        Exposes REST API with GET /products and POST /orders.

        ## API Documentation

        API documentation is generated via Swagger UI available at /api-docs.
    """)
    assert _ids(art) == []


def test_silent_openapi_present():
    """Plan with OpenAPI spec should not fire."""
    art = _plan("""
        # Plan

        ## Deployment

        Release to production.

        Exposes a REST API. The OpenAPI specification is maintained at api/openapi.yaml.
        GET /items returns the product catalogue.
    """)
    assert _ids(art) == []


def test_silent_api_reference_present():
    """Plan mentioning api reference should not fire."""
    art = _plan("""
        # Deployment

        ## Deployment

        Deploy service to GCP.

        Exposes POST /orders endpoint. The API reference is published to the developer portal.
    """)
    assert _ids(art) == []


def test_silent_redoc_present():
    """Plan with Redoc documentation should not fire."""
    art = _plan("""
        # Plan

        ## Deployment

        Deploy to production.

        Exposes REST API. API documentation is served via Redoc at /redoc.
        GET /products returns the product catalogue.
    """)
    assert _ids(art) == []


def test_silent_api_contract_present():
    """Plan mentioning api contract should not fire."""
    art = _plan("""
        # Plan

        ## Deployment

        Release service.

        The API contract is maintained in version control and reviewed on each PR.
        Exposes DELETE /sessions endpoint.
    """)
    assert _ids(art) == []


def test_silent_no_deploy_vocab():
    """Plan with API endpoint vocab but no deployment vocabulary is skipped by guard."""
    art = _plan("""
        # Brainstorm Notes

        We might expose a REST API endpoint eventually for partners.
    """)
    assert _ids(art) == []


def test_silent_no_api_vocab():
    """Plan with deployment vocabulary but no API endpoint vocabulary should not fire."""
    art = _plan("""
        # Deployment Plan

        ## Deployment

        Deploy the service to AWS ECS with Terraform.
        Configure load balancer and auto-scaling group.
    """)
    assert _ids(art) == []


def test_silent_fenced_block():
    """API endpoint vocab inside a fenced code block should not trigger."""
    art = _plan("""
        # Deployment Plan

        ## Deployment

        Deploy to production.

        ```yaml
        paths:
          GET /users:
            summary: List users
          POST /users:
            summary: Create user
        ```
    """)
    assert _ids(art) == []


def test_silent_heading_line():
    """API endpoint vocab on a heading line should not trigger (guard only fires on prose)."""
    art = _plan("""
        # Deployment Plan

        ## Deployment

        Deploy to production server.

        ### GET /health endpoint behaviour

        The service is deployed with health probes configured in Kubernetes.
    """)
    assert _ids(art) == []


def test_silent_spec_artifact():
    """PLAN-MISSING-API-DOCUMENTATION must not fire on spec artifacts."""
    art = _spec("""
        ## Requirements

        FR-001: The system shall expose a REST API endpoint for user registration.
        FR-002: POST /users shall accept a JSON payload and return a user object.
    """)
    assert _ids(art) == []


def test_silent_stoplight_present():
    """Plan mentioning Stoplight API documentation should not fire."""
    art = _plan("""
        # Plan

        ## Deployment

        Deploy service.

        Exposes a GraphQL API endpoint. Stoplight is used to host the API reference and
        generate the OpenAPI spec from annotations.
    """)
    assert _ids(art) == []
