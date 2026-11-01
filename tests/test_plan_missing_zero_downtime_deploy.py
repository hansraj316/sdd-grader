"""Tests for PLAN-MISSING-ZERO-DOWNTIME-DEPLOY pitfall.

Fires when a deployment plan releases to production but specifies no zero-downtime
deployment strategy (blue-green, canary, rolling update, etc.).

Sources: Kiro production-readiness gate; Tessl deployment best practices;
CNCF production readiness review; AWS/GCP blue-green deployment guides.
"""
from __future__ import annotations

import textwrap

from sddgrade.adapters.base import parse_sections
from sddgrade.catalog import load_catalog
from sddgrade.engine.lint import _plan_missing_zero_downtime_deploy
from sddgrade.model import Artifact, ArtifactType

CATALOG = load_catalog()
PITFALL = "PLAN-MISSING-ZERO-DOWNTIME-DEPLOY"


def _make(text: str) -> Artifact:
    src = textwrap.dedent(text)
    return Artifact(
        path="plan.md",
        type=ArtifactType.PLAN,
        raw=src,
        sections=parse_sections(src),
    )


def _ids(art: Artifact) -> list[str]:
    return [f.pitfall_id for f in _plan_missing_zero_downtime_deploy(art, CATALOG)]


# ── FIRE cases (should detect the pitfall) ───────────────────────────────────


def test_fires_simple_to_production():
    art = _make("""\
        # Deployment Plan

        ## Deploy Steps
        Deploy to production via CI pipeline.
        Restart the web server after deployment.
    """)
    assert PITFALL in _ids(art)


def test_fires_production_release_no_strategy():
    art = _make("""\
        # Plan

        ## Deployment

        We will do a production release on Friday at midnight.
        The database migration runs first, then the app server is restarted.
    """)
    assert PITFALL in _ids(art)


def test_fires_go_live_no_strategy():
    art = _make("""\
        # Release Plan

        ## Go-Live Steps

        1. Merge PR to main.
        2. CI builds and pushes Docker image.
        3. Pull and restart containers on go-live server.
    """)
    assert PITFALL in _ids(art)


def test_fires_release_to_prod_no_strategy():
    art = _make("""\
        # Deployment

        ## Release Process
        We will release to prod every two weeks.
        The old process: stop service, replace binary, start service.
    """)
    assert PITFALL in _ids(art)


def test_fires_production_deploy_no_strategy():
    art = _make("""\
        # CI/CD Plan

        ## Production Deployment
        The production deployment runs after staging validation passes.
        We use systemctl restart app to apply the new version.
    """)
    assert PITFALL in _ids(art)


# ── SILENT cases (should NOT detect the pitfall) ─────────────────────────────


def test_silent_blue_green_present():
    art = _make("""\
        # Deployment Plan

        ## Production Deployment
        We use a blue-green deployment strategy.
        Traffic is switched to the green environment after health checks pass.
        Release to production once green is healthy.
    """)
    assert PITFALL not in _ids(art)


def test_silent_canary_release_present():
    art = _make("""\
        # Plan

        ## Deployment
        Deploy to production using a canary release.
        5% of traffic shifts to the new version; monitor for 30 min then proceed.
    """)
    assert PITFALL not in _ids(art)


def test_silent_rolling_update_present():
    art = _make("""\
        # Release Plan

        ## Deploy
        Kubernetes rolling update replaces pods one by one.
        Release to production with maxSurge=1.
    """)
    assert PITFALL not in _ids(art)


def test_silent_zero_downtime_explicit():
    art = _make("""\
        # Deployment Plan

        ## Steps
        Deploy to production with a zero-downtime deployment using ECS.
    """)
    assert PITFALL not in _ids(art)


def test_silent_traffic_shifting_present():
    art = _make("""\
        # Plan

        ## Release
        Production release via traffic shifting: route 10% to v2, monitor, then 100%.
    """)
    assert PITFALL not in _ids(art)


def test_silent_progressive_delivery_present():
    art = _make("""\
        # Deploy

        ## Steps
        Release to production via progressive delivery using Argo Rollouts.
    """)
    assert PITFALL not in _ids(art)


def test_silent_no_deploy_vocab():
    art = _make("""\
        # Architecture Document

        This document describes the system architecture.
        The database uses PostgreSQL with replication.
    """)
    assert PITFALL not in _ids(art)


def test_silent_no_prod_deploy_trigger():
    art = _make("""\
        # Deployment Plan

        ## Steps
        Build the Docker image and push to the registry.
        Run integration tests in the CI environment.
    """)
    assert PITFALL not in _ids(art)


def test_silent_prod_in_fenced_block():
    art = _make("""\
        # Deployment Plan

        ## Steps

        ```
        deploy to production
        ```

        We use Kubernetes rolling update strategy for all releases.
    """)
    assert PITFALL not in _ids(art)


def test_silent_max_surge_kubernetes():
    art = _make("""\
        # Deployment Plan

        ## K8s Config
        Release to production using Kubernetes deployment strategy with
        maxSurge and maxUnavailable for safe rollouts.
    """)
    assert PITFALL not in _ids(art)
