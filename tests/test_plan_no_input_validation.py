"""Tests for PLAN-NO-INPUT-VALIDATION pitfall.

Fires when a plan.md with deployment vocabulary AND API-surface vocabulary (api/REST/
GraphQL/gRPC/HTTP endpoint/webhook/route/request body/request payload/post endpoint)
has no input-validation, sanitization, or schema-validation mention anywhere in the
non-fenced document text.

Source: OWASP API Security Top 10:2023 API6 Unrestricted Access to Sensitive Business
        Flows; OWASP Top 10:2021 A03 Injection; Amazon Kiro production-readiness checklist.
"""
from __future__ import annotations

import textwrap

from sddgrade.adapters.base import parse_sections
from sddgrade.catalog import load_catalog
from sddgrade.engine.lint import _plan_no_input_validation
from sddgrade.model import Artifact, ArtifactType

CATALOG = load_catalog()
PITFALL = "PLAN-NO-INPUT-VALIDATION"


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
    return [f.pitfall_id for f in _plan_no_input_validation(art, CATALOG)]


# ---------------------------------------------------------------------------
# Firing cases — API vocab + deploy vocab, no validation silence token
# ---------------------------------------------------------------------------

def test_fires_rest_api_no_validation():
    """Plan deploys a REST API with no input-validation mention."""
    art = _plan("""
        ## Deployment Plan
        We will release the service to production on Monday.
        The REST API at /v1/orders accepts POST requests from external clients.
        Authentication is handled via JWT tokens.
    """)
    assert _ids(art) == [PITFALL]


def test_fires_graphql_no_sanitization():
    """Plan references a GraphQL endpoint with no sanitization strategy."""
    art = _plan("""
        ## Deployment
        Deploy the GraphQL gateway to the staging environment.
        The resolver will process user-submitted mutation inputs directly.
        No additional access controls are described in this plan.
    """)
    assert _ids(art) == [PITFALL]


def test_fires_webhook_no_schema_check():
    """Plan exposes a webhook endpoint without schema validation."""
    art = _plan("""
        ## Release Plan
        Release the notification service to production this sprint.
        The webhook endpoint at /hooks/github will receive push events.
        Events will be forwarded to the internal queue without preprocessing.
    """)
    assert _ids(art) == [PITFALL]


def test_fires_http_endpoint_no_validation():
    """Plan introduces an HTTP endpoint with no input-validation mention."""
    art = _plan("""
        ## Deployment
        Ship the upload service. The HTTP endpoint /upload accepts multipart form data.
        Files are stored directly to S3 after receiving the request.
    """)
    assert _ids(art) == [PITFALL]


def test_fires_grpc_no_validation():
    """Plan deploys gRPC service with no input-validation strategy."""
    art = _plan("""
        ## Deployment Plan
        Deploy the gRPC catalog service to the production cluster.
        Request messages will be forwarded to the business logic layer.
    """)
    assert _ids(art) == [PITFALL]


def test_fires_request_body_no_validation():
    """Plan mentions request body handling but no validation strategy."""
    art = _plan("""
        ## Production Release
        Deploy the payment service. The request body for POST /checkout is parsed
        and passed directly to the payment processor.
    """)
    assert _ids(art) == [PITFALL]


# ---------------------------------------------------------------------------
# Silent cases — silence token present or guard not met
# ---------------------------------------------------------------------------

def test_silent_when_validate_keyword_present():
    """'validate' keyword silences the check."""
    art = _plan("""
        ## Deployment Plan
        Deploy the REST API to production.
        We validate all incoming request bodies against the OpenAPI schema.
    """)
    assert _ids(art) == []


def test_silent_when_pydantic_present():
    """'pydantic' silences the check."""
    art = _plan("""
        ## Release
        Deploy the FastAPI service to staging.
        All API request payloads are validated using Pydantic models before processing.
    """)
    assert _ids(art) == []


def test_silent_when_zod_present():
    """'zod' silences the check."""
    art = _plan("""
        ## Deployment Plan
        Release the Node.js REST API. All inputs are parsed with Zod schemas.
    """)
    assert _ids(art) == []


def test_silent_when_json_schema_present():
    """'json schema' silences the check."""
    art = _plan("""
        ## Production Release
        Deploy the GraphQL service.
        Request payloads are validated against the JSON schema before execution.
    """)
    assert _ids(art) == []


def test_silent_when_allowlist_present():
    """'allowlist' silences the check."""
    art = _plan("""
        ## Deployment
        Release the REST API. An allowlist of permitted field names is enforced
        on every incoming request.
    """)
    assert _ids(art) == []


def test_silent_when_sanitize_present():
    """'sanitize' silences the check."""
    art = _plan("""
        ## Deploy
        Ship the webhook handler to production.
        All webhook payloads are sanitized before passing to the message queue.
    """)
    assert _ids(art) == []


def test_silent_when_no_api_vocab():
    """Plan with deploy vocab but no API surface — should not fire."""
    art = _plan("""
        ## Deployment Plan
        Deploy the background worker to the production cluster.
        The worker reads from the internal database and runs nightly batch jobs.
    """)
    assert _ids(art) == []


def test_silent_when_no_deploy_vocab():
    """Plan with API vocab but no deploy guard — should not fire."""
    art = _plan("""
        ## Architecture Notes
        The REST API layer routes requests to downstream services.
        This is a purely architectural description with no operational changes.
    """)
    assert _ids(art) == []


def test_silent_on_spec_artifact():
    """PLAN-NO-INPUT-VALIDATION must not fire on spec artifacts."""
    art = _spec("""
        ## Deployment Plan
        Deploy the REST API to production. No validation described.
    """)
    assert _ids(art) == []


def test_silent_when_api_vocab_in_fenced_block():
    """API vocab inside a fenced code block should not satisfy Guard B."""
    art = _plan("""
        ## Deployment Plan
        We will release the backend service to production this week.

        ```bash
        curl -X POST https://api.example.com/v1/orders -d '{}'
        ```

        No public-facing endpoints are introduced in this deployment.
    """)
    assert _ids(art) == []


def test_silent_when_marshmallow_present():
    """'marshmallow' silences the check."""
    art = _plan("""
        ## Deployment
        Deploy the Flask REST API to production.
        Request schemas are enforced with marshmallow before any business logic runs.
    """)
    assert _ids(art) == []


def test_silent_when_request_validation_present():
    """'request validation' silences the check."""
    art = _plan("""
        ## Production Release
        Release the API gateway. Request validation middleware rejects malformed payloads.
        The REST API at /v2/data is protected.
    """)
    assert _ids(art) == []
