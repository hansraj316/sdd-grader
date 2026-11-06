"""Tests for PLAN-NO-CONTENT-SECURITY-POLICY pitfall.

Fires when a deployment plan describes a browser-facing application
(React/Vue/Angular/SPA/Next.js/Nuxt/frontend/web client) but contains
no Content-Security-Policy (CSP) strategy.

Sources: OWASP A03:2021/A05:2021; Kiro security hardening checklist;
Tessl deployment checklist; MDN Content Security Policy guide.
"""
from __future__ import annotations

import textwrap

from sddgrade.adapters.base import parse_sections
from sddgrade.catalog import load_catalog
from sddgrade.engine.lint import _plan_no_content_security_policy
from sddgrade.model import Artifact, ArtifactType

CATALOG = load_catalog()
PITFALL = "PLAN-NO-CONTENT-SECURITY-POLICY"


def _plan(raw: str) -> Artifact:
    raw = textwrap.dedent(raw).strip()
    return Artifact(
        path="plan.md",
        type=ArtifactType.PLAN,
        feature_id="test",
        raw=raw,
        sections=parse_sections(raw),
    )


def _ids(art: Artifact) -> list[str]:
    return [f.pitfall_id for f in _plan_no_content_security_policy(art, CATALOG)]


# ---------------------------------------------------------------------------
# FIRE cases — browser-facing app present, no CSP strategy
# ---------------------------------------------------------------------------


def test_fires_react_spa_no_csp():
    """Plan deploying a React SPA with no CSP strategy fires."""
    art = _plan("""
        # Deployment Plan

        ## Deploy to Production

        Deploy the React SPA to AWS CloudFront backed by S3.
        Static assets are cached with a 1-year TTL.
    """)
    assert PITFALL in _ids(art)


def test_fires_angular_frontend_no_csp():
    """Plan deploying Angular with no CSP strategy fires."""
    art = _plan("""
        # Deployment Plan

        ## Deploy Steps

        1. Build the Angular frontend application.
        2. Push Docker image to ECR.
        3. Deploy to ECS Fargate cluster.
    """)
    assert PITFALL in _ids(art)


def test_fires_vue_spa_no_csp():
    """Plan with Vue SPA served by nginx and no CSP fires."""
    art = _plan("""
        # Deployment Plan

        ## Release

        The Vue SPA is served by nginx from /var/www/html.
        nginx listens on port 443 with TLS termination.
    """)
    assert PITFALL in _ids(art)


def test_fires_nextjs_no_csp():
    """Plan with Next.js deployment and no CSP strategy fires."""
    art = _plan("""
        # Deployment Plan

        ## Deployment

        The Next.js application is containerized with Docker.
        Deploy to Kubernetes using Helm chart.
        Expose via Ingress controller on port 443.
    """)
    assert PITFALL in _ids(art)


def test_fires_frontend_deploy_no_csp():
    """Plan with generic 'frontend' vocabulary and no CSP fires."""
    art = _plan("""
        # Release Plan

        ## Deploy Frontend

        Build and deploy the frontend application to production.
        Static files are served via CloudFront distribution.
    """)
    assert PITFALL in _ids(art)


# ---------------------------------------------------------------------------
# SILENT cases — CSP strategy present or no trigger
# ---------------------------------------------------------------------------


def test_silent_content_security_policy_mentioned():
    """Plan with explicit Content-Security-Policy header does not fire."""
    art = _plan("""
        # Deployment Plan

        ## Deploy to Production

        Deploy the React SPA to production.
        Set Content-Security-Policy header: default-src 'self'; script-src 'self'.
        The CDN is configured to forward the CSP header to browsers.
    """)
    assert PITFALL not in _ids(art)


def test_silent_helmet_mentioned():
    """Plan using Helmet middleware for security headers does not fire."""
    art = _plan("""
        # Deployment Plan

        ## Deploy Steps

        Deploy the Next.js application. The Express server uses Helmet to
        set security headers including HSTS and X-Frame-Options.
        script-src and default-src directives are enforced via Helmet CSP.
    """)
    assert PITFALL not in _ids(art)


def test_silent_csp_acronym():
    """Plan referencing CSP acronym does not fire."""
    art = _plan("""
        # Deployment Plan

        ## Deploy to Production

        Deploy the Angular frontend. Configure CSP via CloudFront response headers.
        The nonce-based policy prevents inline-script injection.
    """)
    assert PITFALL not in _ids(art)


def test_silent_no_deploy_vocab():
    """Document without deploy vocabulary does not fire (not a plan)."""
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
        # This React SPA is not part of this plan
        frontend: out-of-scope
        ```

        No browser-facing services here.
    """)
    assert PITFALL not in _ids(art)


def test_silent_security_headers_mentioned():
    """Plan referencing 'security headers' does not fire."""
    art = _plan("""
        # Deployment Plan

        ## Deploy Steps

        Deploy Vue SPA to production. nginx is configured with security headers
        including HSTS, X-Content-Type-Options, and strict-dynamic enforcement.
    """)
    assert PITFALL not in _ids(art)


def test_silent_script_src_mentioned():
    """Plan with script-src directive does not fire."""
    art = _plan("""
        # Deployment Plan

        ## Deploy to Production

        Deploy the React application. The CDN response policy sets:
        script-src 'self' 'nonce-{nonce}' https://cdn.example.com.
    """)
    assert PITFALL not in _ids(art)


def test_silent_browser_vocab_only_in_heading():
    """Plan where React only appears in heading prose does not fire."""
    art = _plan("""
        # Deployment Plan

        ## Deploy React App to Production

        Server-side API deployment only. The backend Node.js service is
        deployed to ECS. PostgreSQL RDS instance with automated backups.
        No web-layer build steps are in scope for this plan.
    """)
    assert PITFALL not in _ids(art)
