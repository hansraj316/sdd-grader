"""Tests for PLAN-MISSING-HEALTH-CHECK — deployment plans with no health-check or readiness-probe mention."""
from __future__ import annotations

import textwrap

from sddgrade.adapters.base import parse_sections
from sddgrade.catalog import load_catalog
from sddgrade.engine.lint import _plan_missing_health_check
from sddgrade.model import Artifact, ArtifactType

CATALOG = load_catalog()
PITFALL = "PLAN-MISSING-HEALTH-CHECK"


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
    return [f.pitfall_id for f in _plan_missing_health_check(art, CATALOG)]


# ------------------------------------------------------------------ fires cases

def test_fires_on_deployment_section_no_health_check():
    """Plan has a Deployment section but no health-check mention."""
    art = _plan("""
        ## Deployment

        Deploy the service to production using Docker Compose.
        Set environment variables via secrets manager.
    """)
    assert PITFALL in _ids(art)


def test_fires_on_release_vocab_no_health_check():
    """Plan mentions 'release' but no health endpoint."""
    art = _plan("""
        ## Steps

        1. Build the Docker image.
        2. Push to ECR and release to ECS.
        3. Verify that the service is running.
    """)
    assert PITFALL in _ids(art)


def test_fires_on_production_vocab_no_probe():
    """Plan mentions 'production' with no readiness-probe vocabulary."""
    art = _plan("""
        ## Architecture

        The service will be deployed to production on AWS ECS.
        An ALB distributes traffic across containers.
    """)
    assert PITFALL in _ids(art)


def test_fires_on_staging_deploy_no_health():
    """Plan mentions staging deployment with no health-check."""
    art = _plan("""
        ## Deployment

        Ship the build to staging, then promote to production after QA sign-off.
        Use zero-downtime blue/green strategy.
    """)
    assert PITFALL in _ids(art)


def test_fires_on_deploy_no_health_in_kubernetes_plan():
    """Kubernetes plan with rolling update but no health probe."""
    art = _plan("""
        ## Release Plan

        Deploy the new image via `kubectl rollout deploy/myapp`.
        Rolling update with maxUnavailable=0.
    """)
    assert PITFALL in _ids(art)


def test_fires_on_ship_verb_no_health():
    """Plan uses 'ship' vocabulary with no health endpoint."""
    art = _plan("""
        ## Shipping

        We will ship the service after merging to main.
        CI will build and push the container image automatically.
    """)
    assert PITFALL in _ids(art)


# ------------------------------------------------------------------ silent cases

def test_silent_on_no_deployment_vocab():
    """Plan is a pure refactoring plan with no deployment vocabulary."""
    art = _plan("""
        ## Implementation

        Refactor the authentication module to use dependency injection.
        No infrastructure changes required.
    """)
    assert PITFALL not in _ids(art)


def test_silent_when_health_check_mentioned():
    """Plan mentions 'health check' explicitly."""
    art = _plan("""
        ## Deployment

        Deploy to production on ECS.
        Configure the ALB health check at /health with a 30s interval.
    """)
    assert PITFALL not in _ids(art)


def test_silent_when_liveness_probe_mentioned():
    """Plan mentions 'liveness probe'."""
    art = _plan("""
        ## Release

        Deploy to production Kubernetes cluster.
        Set liveness probe: path=/healthz, initialDelaySeconds=10.
    """)
    assert PITFALL not in _ids(art)


def test_silent_when_readiness_probe_mentioned():
    """Plan mentions 'readiness probe'."""
    art = _plan("""
        ## Deployment

        Ship to staging then production.
        Configure readiness probe on /ready before routing traffic.
    """)
    assert PITFALL not in _ids(art)


def test_silent_when_health_endpoint_mentioned():
    """Plan mentions 'health endpoint'."""
    art = _plan("""
        ## Production Deployment

        Expose a health endpoint at /api/health that checks DB connectivity.
        Load balancer will use this to determine instance health.
    """)
    assert PITFALL not in _ids(art)


def test_silent_when_slash_health_path_mentioned():
    """Plan explicitly names the /health path."""
    art = _plan("""
        ## Deployment Section

        Deploy service to production.
        The /health route returns 200 when ready.
    """)
    assert PITFALL not in _ids(art)


def test_silent_when_slash_ping_mentioned():
    """Plan mentions /ping as health signal."""
    art = _plan("""
        ## Release

        Release to production after smoke tests pass.
        Monitor /ping endpoint for availability.
    """)
    assert PITFALL not in _ids(art)


def test_silent_on_spec_artifact():
    """Check does not fire on spec artifacts."""
    raw = textwrap.dedent("""
        ## Deployment

        Deploy to production with no health check mentioned.
    """).strip()
    spec = Artifact(
        path="spec.md",
        type=ArtifactType.SPEC,
        feature_id="test",
        raw=raw,
        sections=parse_sections(raw),
    )
    assert PITFALL not in [f.pitfall_id for f in _plan_missing_health_check(spec, CATALOG)]
