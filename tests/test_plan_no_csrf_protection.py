"""Tests for PLAN-NO-CSRF-PROTECTION pitfall.

Fires when a deployment plan describes a browser-facing application
(React/Vue/Angular/SPA/Next.js/Nuxt/frontend/web client) but contains
no Cross-Site Request Forgery (CSRF) protection strategy.

Sources: OWASP CSRF Prevention Cheat Sheet; OWASP A01:2021;
Kiro security checklist; Tessl deployment checklist.
"""
from __future__ import annotations

import textwrap

from sddgrade.adapters.base import parse_sections
from sddgrade.catalog import load_catalog
from sddgrade.engine.lint import _plan_no_csrf_protection
from sddgrade.model import Artifact, ArtifactType

CATALOG = load_catalog()
PITFALL = "PLAN-NO-CSRF-PROTECTION"


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
    return [f.pitfall_id for f in _plan_no_csrf_protection(art, CATALOG)]


# ---------------------------------------------------------------------------
# FIRE cases — browser-facing app present, no CSRF strategy
# ---------------------------------------------------------------------------


def test_fires_react_spa_no_csrf():
    """Plan deploying a React SPA with no CSRF strategy fires."""
    art = _plan("""
        # Deployment Plan

        ## Deploy to Production

        Deploy the React SPA to AWS CloudFront backed by S3.
        The API uses JWT Bearer tokens and session cookies for authentication.
        Rate limiting is applied via API Gateway.
    """)
    assert PITFALL in _ids(art)


def test_fires_angular_frontend_no_csrf():
    """Plan deploying Angular with no CSRF strategy fires."""
    art = _plan("""
        # Deployment Plan

        ## Deploy Steps

        1. Build the Angular frontend application.
        2. Push Docker image to ECR.
        3. Deploy to ECS Fargate cluster.
        4. Session-based authentication with HttpOnly cookies.
    """)
    assert PITFALL in _ids(art)


def test_fires_vue_spa_no_csrf():
    """Plan with Vue SPA served by nginx and no CSRF fires."""
    art = _plan("""
        # Deployment Plan

        ## Release

        The Vue SPA is served by nginx from /var/www/html.
        nginx listens on port 443 with TLS termination.
        CORS policy is set to allow requests from app.example.com.
    """)
    assert PITFALL in _ids(art)


def test_fires_nextjs_no_csrf():
    """Plan with Next.js deployment and no CSRF strategy fires."""
    art = _plan("""
        # Deployment Plan

        ## Deployment

        The Next.js application is containerized with Docker.
        Deploy to Kubernetes using Helm chart.
        Expose via Ingress controller on port 443.
        Authentication uses session cookies managed by next-auth.
    """)
    assert PITFALL in _ids(art)


def test_fires_frontend_deploy_no_csrf():
    """Plan with generic 'frontend' vocabulary and no CSRF fires."""
    art = _plan("""
        # Release Plan

        ## Deploy Frontend

        Build and deploy the frontend application to production.
        The API is a REST service with cookie-based session management.
        CORS headers are configured to allow the SPA origin.
    """)
    assert PITFALL in _ids(art)


def test_fires_web_client_no_csrf():
    """Plan deploying a web client with no CSRF fires."""
    art = _plan("""
        # Deployment Plan

        ## Deploy

        Deploy the backend API and web client to production.
        Authentication uses HttpOnly session cookies.
        Observability: Datadog APM and log aggregation.
    """)
    assert PITFALL in _ids(art)


# ---------------------------------------------------------------------------
# SILENT cases — CSRF strategy present or no trigger
# ---------------------------------------------------------------------------


def test_silent_csrf_token_mentioned():
    """Plan with CSRF token strategy does not fire."""
    art = _plan("""
        # Deployment Plan

        ## Deploy to Production

        Deploy the React SPA to production.
        CSRF protection: include a CSRF token in all state-changing requests.
        The token is generated server-side and embedded in the meta tag.
    """)
    assert PITFALL not in _ids(art)


def test_silent_samesite_mentioned():
    """Plan setting SameSite cookie attribute does not fire."""
    art = _plan("""
        # Deployment Plan

        ## Deploy Steps

        Deploy the Next.js application. Session cookies are set with
        SameSite=Strict, HttpOnly, and Secure attributes.
        This prevents CSRF attacks from cross-origin sites.
    """)
    assert PITFALL not in _ids(art)


def test_silent_double_submit_mentioned():
    """Plan using double-submit cookie pattern does not fire."""
    art = _plan("""
        # Deployment Plan

        ## Deploy to Production

        Deploy the Angular frontend.
        CSRF defence: double-submit cookie pattern — the client reads
        a CSRF cookie and includes the same value in the X-CSRF-Token header.
    """)
    assert PITFALL not in _ids(art)


def test_silent_csurf_mentioned():
    """Plan using csurf middleware does not fire."""
    art = _plan("""
        # Deployment Plan

        ## Deploy Steps

        Deploy the Vue SPA backed by an Express API.
        The Express server uses csurf middleware for CSRF protection.
        JWT is used for stateless API endpoints.
    """)
    assert PITFALL not in _ids(art)


def test_silent_no_deploy_vocab():
    """Document without deploy vocabulary does not fire."""
    art = _plan("""
        ## Overview

        This document describes a React application design.
        Architecture notes only — no CI/CD pipeline steps included.
    """)
    assert PITFALL not in _ids(art)


def test_silent_no_browser_vocab():
    """Plan with no browser-facing app vocabulary does not fire."""
    art = _plan("""
        # Deployment Plan

        ## Deploy Steps

        Deploy the gRPC service to Kubernetes.
        Apply resource limits and configure liveness probes.
        No browser-facing endpoints are exposed.
    """)
    assert PITFALL not in _ids(art)


def test_silent_browser_vocab_in_fence():
    """Browser vocab inside a fenced code block does not trigger."""
    art = _plan("""
        # Deployment Plan

        ## Deploy Steps

        Deploy backend services to production.

        ```yaml
        # This React SPA is out of scope
        frontend: out-of-scope
        ```

        No browser-facing services in this deployment.
    """)
    assert PITFALL not in _ids(art)


def test_silent_browser_vocab_only_in_heading():
    """Plan where React only appears in a heading does not fire."""
    art = _plan("""
        # Deployment Plan

        ## Deploy React App to Production

        Server-side API deployment only. The backend Node.js service is
        deployed to ECS. PostgreSQL RDS instance with automated backups.
        No web-layer build steps are in scope for this plan.
    """)
    assert PITFALL not in _ids(art)


def test_silent_non_plan_artifact():
    """Non-plan artifact does not fire even with browser and no CSRF vocab."""
    art = _spec("""
        # Feature Spec

        ## Requirements

        FR-001: The system shall deploy a React SPA to production.
        FR-002: Deploy steps should be automated via CI/CD.
        FR-003: The application shall use cookie-based authentication.
    """)
    assert PITFALL not in _ids(art)


def test_silent_x_csrf_token_mentioned():
    """Plan referencing X-CSRF-Token header does not fire."""
    art = _plan("""
        # Deployment Plan

        ## Deploy Steps

        Deploy the Angular application.
        All state-changing API calls include the X-CSRF-Token header.
        The backend validates the token before processing mutations.
    """)
    assert PITFALL not in _ids(art)
