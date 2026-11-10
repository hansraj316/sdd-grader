"""Tests for PLAN-MISSING-CDN pitfall check.

Fires when a plan.md with deployment vocabulary AND browser-facing or static-asset
vocabulary has no CDN or edge-caching strategy anywhere in the non-fenced text.

Source: Tessl deployment checklist; AWS Well-Architected PE-11; Google Core Web Vitals.
"""
from __future__ import annotations

import textwrap

from sddgrade.adapters.base import parse_sections
from sddgrade.catalog import load_catalog
from sddgrade.engine.lint import _plan_missing_cdn
from sddgrade.model import Artifact, ArtifactType

CATALOG = load_catalog()
PITFALL = "PLAN-MISSING-CDN"


def _plan(raw: str) -> Artifact:
    raw = textwrap.dedent(raw).strip()
    return Artifact(
        path="plan.md",
        type=ArtifactType.PLAN,
        feature_id="test",
        raw=raw,
        sections=parse_sections(raw),
    )


def _fires(raw: str) -> bool:
    findings = _plan_missing_cdn(_plan(raw), CATALOG)
    return any(f.pitfall_id == PITFALL for f in findings)


# ---------------------------------------------------------------------------
# Fire cases (≥5)
# ---------------------------------------------------------------------------

def test_spa_plan_no_cdn():
    """SPA deployment plan with no CDN should fire."""
    assert _fires(
        """\
        ## Deployment

        We deploy a SPA built with Webpack to an S3 bucket.
        The frontend is served directly from the origin server.
        """
    )


def test_react_plan_no_cdn():
    """React app deployment with no CDN should fire."""
    assert _fires(
        """\
        ## Deployment Plan

        Deploy the React application to an EC2 instance running nginx.
        Assets are served from the application server on port 80.
        """
    )


def test_static_assets_no_cdn():
    """Plan mentioning static assets but no CDN should fire."""
    assert _fires(
        """\
        ## Release Plan

        We deploy to production on Kubernetes.
        Static assets are stored in a GCS bucket and served by the app server.
        """
    )


def test_angular_plan_no_cdn():
    """Angular deployment plan with no CDN should fire."""
    assert _fires(
        """\
        ## Deployment

        The Angular application is deployed to a Linux VM.
        No edge caching has been configured.
        """
    )


def test_frontend_plan_no_cdn():
    """Frontend deployment plan with no CDN should fire."""
    assert _fires(
        """\
        ## Deployment

        We release the frontend to our staging environment via Docker.
        No edge strategy is documented here.
        """
    )


def test_nuxt_plan_no_cdn():
    """Nuxt.js deployment without CDN should fire."""
    assert _fires(
        """\
        ## Deployment

        Deploy the Nuxt application to a DigitalOcean droplet.
        Static files are served from the app server.
        """
    )


def test_svelte_plan_no_cdn():
    """Svelte app deployment without CDN should fire."""
    assert _fires(
        """\
        ## Deployment

        The Svelte application deploys to Render.
        No edge layer configured for asset delivery.
        """
    )


# ---------------------------------------------------------------------------
# Silent cases (≥9)
# ---------------------------------------------------------------------------

def test_cloudfront_silences():
    """Plan with CloudFront mentioned should not fire."""
    assert not _fires(
        """\
        ## Deployment

        Deploy the React app to S3 and serve via CloudFront.
        Cache-control headers set per asset type.
        """
    )


def test_cloudflare_silences():
    """Plan with Cloudflare CDN should not fire."""
    assert not _fires(
        """\
        ## Deployment

        The SPA is served behind Cloudflare for CDN caching.
        Assets are cached at the edge globally.
        """
    )


def test_edge_cache_silences():
    """Plan with edge cache strategy should not fire."""
    assert not _fires(
        """\
        ## Deployment

        Frontend assets are deployed and distributed via edge cache nodes.
        The CDN invalidation hook runs on every deploy.
        """
    )


def test_static_hosting_silences():
    """Plan with static hosting mentioned should not fire."""
    assert not _fires(
        """\
        ## Deployment

        React application uses Firebase static hosting with global distribution.
        """
    )


def test_cache_control_header_silences():
    """Plan with cache-control headers strategy should not fire."""
    assert not _fires(
        """\
        ## Deployment

        Frontend assets are deployed to S3.
        cache-control headers are set to max-age=31536000 for hashed JS/CSS bundles.
        """
    )


def test_non_browser_plan_no_trigger():
    """Backend-only plan with no browser/static vocab should not fire."""
    assert not _fires(
        """\
        ## Deployment

        Deploy the Python microservice to Kubernetes.
        No browser-facing components in this service.
        """
    )


def test_no_deploy_section_no_fire():
    """Document with browser vocab but no deploy section/vocab should not fire."""
    assert not _fires(
        """\
        ## Overview

        This is a spec for the React frontend architecture.
        Scope is frontend only; infrastructure excluded.
        """
    )


def test_fenced_block_excluded():
    """Browser vocab inside a fenced code block should not trigger."""
    assert not _fires(
        """\
        ## Deployment

        We deploy to production.
        ```
        const app = new React.Component();
        // deploy SPA to server
        ```
        No other browser-related references exist here.
        """
    )


def test_heading_line_excluded():
    """Browser vocab on a heading line should not trigger."""
    assert not _fires(
        """\
        ## Deployment Plan

        # React Frontend (not in scope)

        We deploy only the backend service to Kubernetes.
        No browser-facing deployment here.
        """
    )


def test_fastly_silences():
    """Plan with Fastly CDN should not fire."""
    assert not _fires(
        """\
        ## Deployment

        The Angular application uses Fastly for edge delivery of static assets.
        """
    )


def test_content_delivery_silences():
    """Plan with content delivery mention should not fire."""
    assert not _fires(
        """\
        ## Deployment

        The frontend is distributed via our content delivery network.
        React bundles are cached globally with 1-year TTL.
        """
    )
