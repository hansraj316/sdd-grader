"""Tests for SPEC-MISSING-ERROR-CODES pitfall.

Fires when a spec defines API/HTTP operations (FR-/NFR- lines + API vocab) but
contains no error response or HTTP status code specification.

Sources: MAQA binary-verifiability; OpenAPI best practices; ISO/IEC 25010:2023
§4.2.4 fault tolerance; IBM RQA completeness.
"""
from __future__ import annotations

import textwrap

from sddgrade.adapters.base import parse_sections
from sddgrade.catalog import load_catalog
from sddgrade.engine.lint import _spec_missing_error_codes
from sddgrade.model import Artifact, ArtifactType

CATALOG = load_catalog()
PITFALL = "SPEC-MISSING-ERROR-CODES"


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
    return [f.pitfall_id for f in _spec_missing_error_codes(art, CATALOG)]


# ---------------------------------------------------------------------------
# Firing cases
# ---------------------------------------------------------------------------


def test_fires_rest_api_no_error_codes():
    """Spec mentions REST API endpoint in requirements but no error responses."""
    art = _spec("""
        # User Management API

        ## Requirements

        FR-001: The system shall expose a REST API endpoint for user creation.
        FR-002: The API endpoint shall accept a JSON request body with name and email.
        FR-003: The system shall return the created user ID in the response body.
        FR-004: The API shall require authentication via JWT token.
        FR-005: The system shall validate the email format in the request body.
    """)
    assert PITFALL in _ids(art)


def test_fires_http_method_no_error_codes():
    """Spec uses HTTP GET/POST method vocab with no status codes."""
    art = _spec("""
        # Product Catalog API

        ## Functional Requirements

        FR-001: The system shall implement an HTTP GET endpoint for product listing.
        FR-002: The HTTP POST endpoint shall accept product creation payloads.
        FR-003: The system shall return paginated results in the response body.
        NFR-001: The API call shall complete within 200ms under normal load.
    """)
    assert PITFALL in _ids(art)


def test_fires_api_endpoint_shall_no_error_spec():
    """Spec with 'API shall' and no error handling."""
    art = _spec("""
        # Order Processing

        ## Requirements

        FR-001: The API shall accept order creation requests.
        FR-002: The API shall validate inventory before confirming.
        FR-003: The system shall return a confirmation number in the response body.
        FR-004: The API shall support idempotency keys in the request body.
    """)
    assert PITFALL in _ids(art)


def test_fires_endpoints_shall_no_error_vocab():
    """Spec uses 'endpoints shall' without error specifications."""
    art = _spec("""
        # Notification Service

        ## Functional Requirements

        FR-001: The endpoints shall require valid authentication tokens.
        FR-002: The system shall process HTTP request payloads asynchronously.
        FR-003: The service shall send notifications via HTTP method calls.
        NFR-001: The system shall process API calls within 500ms.
        NFR-002: The system shall support 1000 concurrent API requests.
    """)
    assert PITFALL in _ids(art)


# ---------------------------------------------------------------------------
# Silent cases
# ---------------------------------------------------------------------------


def test_silent_has_4xx_mention():
    """Spec mentions 4xx codes — silence."""
    art = _spec("""
        # File Upload API

        ## Requirements

        FR-001: The API endpoint shall accept multipart file uploads.
        FR-002: The system shall validate file size in the request body.
        FR-003: The API shall return 4xx on validation failure.
        FR-004: The system shall store files in object storage.
    """)
    assert PITFALL not in _ids(art)


def test_silent_has_specific_http_status_code():
    """Spec mentions specific HTTP status code 404 — silence."""
    art = _spec("""
        # Resource API

        ## Requirements

        FR-001: The REST API endpoint shall fetch resources by ID.
        FR-002: The API call shall return HTTP 404 when the resource does not exist.
        FR-003: The system shall return the full resource in the response body.
        NFR-001: The system shall respond within 100ms.
    """)
    assert PITFALL not in _ids(art)


def test_silent_has_error_response_mention():
    """Spec has 'error response' vocab — silence."""
    art = _spec("""
        # Payment API

        ## Requirements

        FR-001: The API endpoint shall process payment requests.
        FR-002: The system shall return an error response when the card is declined.
        FR-003: The API shall accept payment details in the request body.
        NFR-001: The system shall process API calls within 2 seconds.
    """)
    assert PITFALL not in _ids(art)


def test_silent_has_error_handling_mention():
    """Spec has 'error handling' vocab — silence."""
    art = _spec("""
        # Search API

        ## Requirements

        FR-001: The REST API endpoint shall support full-text search.
        FR-002: The system shall implement error handling for malformed queries.
        FR-003: The API call shall return paginated results.
        NFR-001: The response body shall include pagination metadata.
    """)
    assert PITFALL not in _ids(art)


def test_silent_has_status_code_mention():
    """Spec has 'status code' vocab — silence."""
    art = _spec("""
        # Auth Service

        ## Requirements

        FR-001: The API endpoint shall validate credentials in the request body.
        FR-002: The system shall return appropriate HTTP status codes.
        FR-003: The HTTP response body shall include a JWT token on success.
        FR-004: The API shall expire tokens after 24 hours.
    """)
    assert PITFALL not in _ids(art)


def test_silent_has_5xx_mention():
    """Spec mentions 5xx codes — silence."""
    art = _spec("""
        # Webhook Service

        ## Requirements

        FR-001: The system shall deliver events via HTTP POST to registered endpoints.
        FR-002: The API call shall retry on 5xx responses from the destination.
        FR-003: The system shall store webhook payloads in the request body log.
        NFR-001: The system shall process requests within 200ms.
    """)
    assert PITFALL not in _ids(art)


def test_silent_no_api_vocab():
    """Spec has requirements but no API/HTTP vocabulary — silence."""
    art = _spec("""
        # Report Generation

        ## Requirements

        FR-001: The system shall generate monthly sales reports.
        FR-002: The report shall include revenue by product category.
        FR-003: The system shall export reports in PDF and CSV formats.
        NFR-001: The system shall generate reports within 30 seconds.
    """)
    assert PITFALL not in _ids(art)


def test_silent_fewer_than_three_req_ids():
    """Spec has API vocab but fewer than 3 FR-/NFR- lines — guard not met."""
    art = _spec("""
        # Simple API

        FR-001: The API endpoint shall return a greeting.
        FR-002: The response body shall be JSON.
    """)
    assert PITFALL not in _ids(art)


def test_silent_non_spec_artifact():
    """Non-spec artifacts are ignored."""
    raw = textwrap.dedent("""
        # Deployment Plan

        FR-001: The API endpoint shall be deployed to Kubernetes.
        FR-002: The HTTP request rate shall be limited.
        FR-003: The response body shall be cached.
    """).strip()
    art = Artifact(
        path="plan.md",
        type=ArtifactType.PLAN,
        feature_id="test",
        raw=raw,
        sections=parse_sections(raw),
    )
    assert PITFALL not in [f.pitfall_id for f in _spec_missing_error_codes(art, CATALOG)]


def test_silent_failure_response_mention():
    """Spec has 'failure response' — silence."""
    art = _spec("""
        # Transfer API

        ## Requirements

        FR-001: The API shall process money transfers via the HTTP POST endpoint.
        FR-002: The system shall return a failure response when funds are insufficient.
        FR-003: The request body shall include source and destination account IDs.
        NFR-001: The API call shall be idempotent.
    """)
    assert PITFALL not in _ids(art)
