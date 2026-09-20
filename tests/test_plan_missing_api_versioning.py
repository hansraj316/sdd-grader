"""Tests for PLAN-MISSING-API-VERSIONING pitfall.

Fires when a plan.md with deployment vocabulary AND API-change vocabulary
(new endpoint, adds REST route, exposes API, modifies API contract, etc.)
has NO API versioning or backward-compatibility strategy anywhere in the document.

Sources: OpenSpec (version-stable contracts), Spec-Kit (consumer-contract stability),
         ISO/IEC/IEEE 29148:2018 §5.2.7 (compatibility), Tessl (consumer-contract stability).
"""
from __future__ import annotations

import textwrap

from sddgrade.adapters.base import parse_sections
from sddgrade.catalog import load_catalog
from sddgrade.engine.lint import _plan_missing_api_versioning
from sddgrade.model import Artifact, ArtifactType

CATALOG = load_catalog()
PITFALL = "PLAN-MISSING-API-VERSIONING"


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
    return [f.pitfall_id for f in _plan_missing_api_versioning(art, CATALOG)]


# ---------------------------------------------------------------------------
# Firing cases — API-change vocab present, no versioning strategy
# ---------------------------------------------------------------------------


def test_fires_new_endpoint_no_versioning():
    """Plan adds a new endpoint but states no versioning strategy."""
    art = _plan("""
        ## Deployment Plan
        Deploy the payments service to production.
        A new endpoint /payments/refund is introduced to handle refund requests.
        The endpoint accepts JSON and returns a 202 Accepted on success.
        Deployment proceeds with a rolling update, one instance at a time.
    """)
    assert PITFALL in _ids(art)


def test_fires_adds_rest_endpoint_no_version():
    """Plan adds a REST endpoint with no versioning."""
    art = _plan("""
        ## Release Plan
        Deploy the reporting feature to production.
        Adding a REST endpoint GET /reports/summary for dashboard consumers.
        The endpoint requires an Authorization header.
        Deployment: blue-green swap after smoke tests pass.
    """)
    assert PITFALL in _ids(art)


def test_fires_exposes_api_no_version():
    """Plan exposes an API route with no versioning policy."""
    art = _plan("""
        ## Production Deployment
        Release the partner integration feature.
        The service now exposes an API route /partners/sync for third-party consumers.
        Authentication is via HMAC-signed requests.
        Deployment: canary at 5% for one hour, then full rollout.
    """)
    assert PITFALL in _ids(art)


def test_fires_modifies_api_contract_no_version():
    """Plan modifies an API contract with no backward-compat mention."""
    art = _plan("""
        ## Deployment Plan
        Deploy the search service update.
        This release modifies the API contract for /search/results by adding a
        required query parameter `locale`.
        Deployment: rolling update across the fleet.
    """)
    assert PITFALL in _ids(art)


def test_fires_introduces_endpoint_no_version():
    """Plan introduces an HTTP endpoint with no versioning."""
    art = _plan("""
        ## Release Deployment
        Ship the notification service to production.
        This release introduces an HTTP endpoint POST /notifications/send.
        The payload is a JSON object with `recipient` and `message` fields.
        Deployment via CI/CD pipeline with automated smoke tests.
    """)
    assert PITFALL in _ids(art)


def test_fires_api_route_add_no_version():
    """Plan adds a route via keyword order `route add`."""
    art = _plan("""
        ## Deployment Plan
        Deploy the file management service to production.
        Route /files/upload is added to handle multipart uploads.
        The route requires OAuth2 bearer token authentication.
        Rolling deployment with health-check gate.
    """)
    assert PITFALL in _ids(art)


# ---------------------------------------------------------------------------
# Silent cases — API versioning vocabulary present
# ---------------------------------------------------------------------------


def test_silent_url_version_prefix():
    """Plan mentions /v2/ path prefix — silent."""
    art = _plan("""
        ## Deployment Plan
        Deploy the payments service to production.
        A new endpoint /v2/payments/refund is introduced.
        /v1/payments/refund remains available during the deprecation window.
        Deployment: blue-green swap.
    """)
    assert PITFALL not in _ids(art)


def test_silent_semver_mention():
    """Plan mentions semver versioning — silent."""
    art = _plan("""
        ## Release Plan
        Deploy the reporting API to production.
        Adding REST endpoint GET /reports/summary.
        This is a semver minor release (v2.3.0); the endpoint is additive and
        backward-compatible with all v2.x consumers.
        Deployment: rolling update.
    """)
    assert PITFALL not in _ids(art)


def test_silent_deprecation_mention():
    """Plan states a deprecation policy — silent."""
    art = _plan("""
        ## Production Deployment
        Deploy the partner integration service.
        Exposes API route /partners/sync for third-party consumers.
        The legacy /partner/push endpoint is deprecated and will be removed
        in the next major release (90-day sunset).
        Deployment: canary then full rollout.
    """)
    assert PITFALL not in _ids(art)


def test_silent_backward_compat_mention():
    """Plan explicitly states backward-compat — silent."""
    art = _plan("""
        ## Deployment Plan
        Deploy the search service update.
        This release modifies the API contract by adding an optional `locale` parameter.
        The change is backward-compatible; existing clients without `locale` receive
        default behaviour unchanged.
        Rolling deployment across the fleet.
    """)
    assert PITFALL not in _ids(art)


def test_silent_breaking_change_mention():
    """Plan acknowledges breaking-change — silent (shows awareness)."""
    art = _plan("""
        ## Release Deployment
        Ship notification service to production.
        Introduces HTTP endpoint POST /notifications/send.
        Note: this is a breaking-change for v1 clients; migration guide published.
        Deployment via CI/CD.
    """)
    assert PITFALL not in _ids(art)


def test_silent_api_version_header():
    """Plan mentions api-version header — silent."""
    art = _plan("""
        ## Deployment Plan
        Deploy the file service to production.
        New endpoint /files/upload added.
        Consumers must pass the api-version header to select the API contract.
        Deployment: rolling update.
    """)
    assert PITFALL not in _ids(art)


def test_silent_consumer_driven_mention():
    """Plan references consumer-driven contract testing — silent."""
    art = _plan("""
        ## Deployment Plan
        Deploy the payment gateway to production.
        A new endpoint /payments/validate is introduced.
        Consumer-driven contract tests run in CI before every deploy.
        Rolling deployment with smoke tests.
    """)
    assert PITFALL not in _ids(art)


def test_silent_no_api_change_vocab():
    """Plan has no API-change vocabulary at all — silent."""
    art = _plan("""
        ## Deployment Plan
        Deploy the billing service to production.
        Payments are processed via Stripe.
        Database: PostgreSQL 15 on RDS.
        Deployment: blue-green with automated rollback.
    """)
    assert PITFALL not in _ids(art)


def test_silent_no_deploy_guard():
    """Document mentions API endpoint but no deployment vocabulary — not a plan."""
    art = _plan("""
        ## Architecture Notes
        A new endpoint /data/export is discussed here.
        This document is for architecture reference purposes only.
    """)
    assert PITFALL not in _ids(art)


def test_silent_spec_artifact():
    """Spec artifact — PLAN-MISSING-API-VERSIONING does not apply."""
    art = _spec("""
        ## Requirements
        FR-001: The system SHALL expose a new endpoint /users/profile.
        FR-002: The endpoint SHALL return a JSON payload.
        No deployment information is included here.
    """)
    assert PITFALL not in _ids(art)


def test_silent_api_change_in_fenced_code():
    """API-change vocab inside a fenced code block — silent."""
    art = _plan("""
        ## Deployment Plan
        Deploy the recommendation service to production.
        The service is stateless; all state lives in the database.

        ```yaml
        routes:
          - path: /v1/recommendations
            method: GET
            # new endpoint added here for internal reference
        ```

        Deployment: rolling update with health-check gate.
    """)
    assert PITFALL not in _ids(art)
