"""Tests for PLAN-MISSING-CORS-POLICY pitfall.

Fires when a plan.md with deployment vocabulary AND browser-facing API vocabulary
(SPA/React/Vue/Angular/Next.js/Nuxt/frontend/web client) has no CORS policy
anywhere in the non-fenced text.

Source: OWASP API07:2023 Security Misconfiguration,
        Tessl deployment checklist,
        Kiro production-readiness gate.
"""
from __future__ import annotations

import textwrap

from sddgrade.adapters.base import parse_sections
from sddgrade.catalog import load_catalog
from sddgrade.engine.lint import _plan_missing_cors_policy
from sddgrade.model import Artifact, ArtifactType

CATALOG = load_catalog()
PITFALL = "PLAN-MISSING-CORS-POLICY"


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
    return [f.pitfall_id for f in _plan_missing_cors_policy(art, CATALOG)]


# ---------------------------------------------------------------------------
# Firing cases — browser-facing API vocab + deploy vocab, no CORS silence
# ---------------------------------------------------------------------------

def test_fires_spa_no_cors():
    """Plan describes an SPA calling the API with no CORS policy."""
    art = _plan("""
        ## Deployment Plan
        Deploy the user profile service to production this sprint.
        The SPA calls the REST API directly from the browser.
        Authentication is handled via JWT tokens in Authorization headers.
    """)
    assert _ids(art) == [PITFALL]


def test_fires_react_frontend_no_cors():
    """Plan mentions React frontend with no CORS policy."""
    art = _plan("""
        ## Production Release
        Release the e-commerce platform backend API.
        The React frontend makes fetch calls to /api/v1/products.
        The API is deployed to a separate subdomain from the frontend.
    """)
    assert _ids(art) == [PITFALL]


def test_fires_vue_client_no_cors():
    """Plan mentions Vue client with no CORS policy."""
    art = _plan("""
        ## Release Plan
        Deploy the inventory management API to the production cluster.
        The Vue dashboard consumes the REST API for real-time updates.
        No additional authentication configuration is required.
    """)
    assert _ids(art) == [PITFALL]


def test_fires_angular_app_no_cors():
    """Plan mentions Angular application with no CORS policy."""
    art = _plan("""
        ## Deployment
        Ship the reporting microservice to production.
        The Angular app calls the reporting API from the client browser.
        The API is hosted on api.example.com separate from the frontend origin.
    """)
    assert _ids(art) == [PITFALL]


def test_fires_nextjs_no_cors():
    """Plan mentions Next.js client-side calls with no CORS policy."""
    art = _plan("""
        ## Production Rollout
        Deploy the notifications API to the cloud environment.
        The Next.js frontend makes browser-side fetch calls to the API.
        The API key is stored in environment variables.
    """)
    assert _ids(art) == [PITFALL]


def test_fires_frontend_no_cors():
    """Plan mentions generic frontend API calls with no CORS policy."""
    art = _plan("""
        ## Deploy
        Release the new feature to staging, then production.
        The frontend calls the new /api/v2/search endpoint directly.
        No infrastructure changes are required beyond the API container.
    """)
    assert _ids(art) == [PITFALL]


# ---------------------------------------------------------------------------
# Silent cases — CORS vocabulary present or trigger absent
# ---------------------------------------------------------------------------

def test_silent_cors_keyword():
    """Plan explicitly mentions CORS — check silenced."""
    art = _plan("""
        ## Deployment Plan
        Deploy the user profile API to production.
        The React frontend calls the API from the browser.
        CORS is configured to allow requests from https://app.example.com only.
    """)
    assert _ids(art) == []


def test_silent_access_control_allow_origin():
    """Plan states Access-Control-Allow-Origin header — check silenced."""
    art = _plan("""
        ## Production Release
        Release the e-commerce API.
        The SPA calls the backend from the browser.
        The API sets Access-Control-Allow-Origin: https://store.example.com
        on all responses.
    """)
    assert _ids(art) == []


def test_silent_cors_middleware():
    """Plan mentions CORS middleware — check silenced."""
    art = _plan("""
        ## Release Plan
        Deploy the data API to production.
        The Angular app makes browser requests to the API.
        The FastAPI service uses cors middleware configured for the frontend origin.
    """)
    assert _ids(art) == []


def test_silent_preflight():
    """Plan mentions preflight requests — check silenced."""
    art = _plan("""
        ## Deployment
        Ship the search API to production.
        The Vue frontend calls the search endpoint from the browser.
        The server handles preflight OPTIONS requests with the correct headers.
    """)
    assert _ids(art) == []


def test_silent_same_origin():
    """Plan mentions same-origin policy — check silenced."""
    art = _plan("""
        ## Production Rollout
        Deploy the payment API.
        The Next.js frontend is served from the same origin as the API.
        The same-origin policy provides default browser protection.
    """)
    assert _ids(art) == []


def test_silent_no_browser_api_vocab():
    """Plan has no browser-facing API vocabulary — check does not fire."""
    art = _plan("""
        ## Deployment Plan
        Deploy the internal batch processing service to production.
        Workers consume messages from the queue and write results to the database.
        No browser clients interact with this service.
    """)
    assert _ids(art) == []


def test_silent_spec_artifact():
    """PLAN-MISSING-CORS-POLICY must not fire on a spec artifact."""
    art = _spec("""
        ## Deployment Plan
        Deploy the user API to production.
        The React frontend makes requests to the API from the browser.
        No CORS policy is defined in this document.
    """)
    assert _ids(art) == []


def test_silent_no_deploy_vocab():
    """Plan artifact type but no deploy vocabulary — guard not satisfied."""
    art = _plan("""
        ## Architecture Notes
        The SPA will eventually call the REST API.
        The React component fetches data from the backend.
        This is a high-level architecture overview only.
    """)
    assert _ids(art) == []


def test_silent_fenced_trigger():
    """Browser API vocab only inside fenced code block — should not fire."""
    art = _plan("""
        ## Deployment Plan
        Deploy the backend API to production this sprint.

        ```javascript
        // Example SPA fetch call
        fetch('https://api.example.com/data')
        // React component makes a request
        ```

        All API calls originate from server-side workers only.
    """)
    assert _ids(art) == []


def test_silent_cors_headers_keyword():
    """Plan mentions cors headers — check silenced."""
    art = _plan("""
        ## Production Release
        Deploy the notifications API.
        The frontend makes browser requests to the API.
        The API gateway is configured with cors headers for the allowed domains.
    """)
    assert _ids(art) == []
