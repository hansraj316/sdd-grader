"""Tests for PLAN-MISSING-ROLLBACK — deployment plans missing a rollback strategy."""
from __future__ import annotations

import textwrap

from sddgrade.adapters.base import parse_sections
from sddgrade.catalog import load_catalog
from sddgrade.engine.lint import _plan_missing_rollback
from sddgrade.model import Artifact, ArtifactType

CATALOG = load_catalog()
PITFALL = "PLAN-MISSING-ROLLBACK"


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
    return [f.pitfall_id for f in _plan_missing_rollback(art, CATALOG)]


# ------------------------------------------------------------------ fires cases

def test_fires_on_deploy_section_no_rollback():
    """Plan has a Deployment section but no rollback/revert mention."""
    art = _plan("""
        ## Deployment

        Run `kubectl apply -f manifests/api.yaml` to deploy the new image.
        Monitor pod status with `kubectl get pods`.
    """)
    assert PITFALL in _ids(art)


def test_fires_on_deploy_vocab_no_rollback():
    """Plan uses 'deploy' keyword in prose but never mentions recovery."""
    art = _plan("""
        ## Steps

        1. Deploy the service to production using the CI pipeline.
        2. Verify health check endpoint returns 200.
    """)
    assert PITFALL in _ids(art)


def test_fires_on_ship_vocab_no_rollback():
    """'ship' counts as deployment vocabulary."""
    art = _plan("""
        ## Release

        Ship the new version to staging, then promote to production.
    """)
    assert PITFALL in _ids(art)


def test_fires_on_release_section_no_rollback():
    """Release section header triggers the guard."""
    art = _plan("""
        ## Release

        Tag v2.1.0, push the Docker image, and update the helm chart.
    """)
    assert PITFALL in _ids(art)


def test_fires_on_staging_vocab_no_rollback():
    """'staging' in deployment vocabulary triggers the guard."""
    art = _plan("""
        ## Implementation Steps

        Deploy the feature to staging first, then production after QA sign-off.
    """)
    assert PITFALL in _ids(art)


# ------------------------------------------------------------------ silent cases

def test_silent_when_rollback_keyword_present():
    """Plan mentions 'rollback' explicitly — check should be silent."""
    art = _plan("""
        ## Deployment

        Deploy to production with `kubectl apply`.

        ## Rollback

        If the deploy fails, run `kubectl rollout undo deployment/api` to rollback.
    """)
    assert PITFALL not in _ids(art)


def test_silent_when_revert_present():
    """'revert' anywhere in the document satisfies the check."""
    art = _plan("""
        ## Deployment

        Push image to registry and deploy.
        If issues arise, revert to the previous image tag.
    """)
    assert PITFALL not in _ids(art)


def test_silent_when_fallback_present():
    """'fallback' satisfies the rollback check."""
    art = _plan("""
        ## Steps

        Deploy the new service. The load balancer has a fallback to v1 if health checks fail.
    """)
    assert PITFALL not in _ids(art)


def test_silent_when_recovery_present():
    """'recovery' satisfies the rollback check."""
    art = _plan("""
        ## Deployment

        Deploy to production. Recovery procedure: re-deploy from previous artifact.
    """)
    assert PITFALL not in _ids(art)


def test_silent_when_undo_present():
    """'undo' satisfies the rollback check."""
    art = _plan("""
        ## Release Plan

        Ship release candidate. If it fails smoke tests, undo the deployment.
    """)
    assert PITFALL not in _ids(art)


def test_silent_pure_refactoring_plan_no_deploy_vocab():
    """Pure refactoring plan with no deployment vocabulary — guard prevents false positive."""
    art = _plan("""
        ## Overview

        Rename the UserService class to AccountService throughout the codebase.
        Update all imports and run the test suite.

        ## Steps

        1. Find all references with `rg UserService`.
        2. Replace with AccountService.
        3. Run `pytest`.
    """)
    assert PITFALL not in _ids(art)


def test_silent_on_spec_artifact():
    """The pitfall only applies to plan.md, not spec.md."""
    art = _spec("""
        ## Overview

        Deploy the API to production.
    """)
    assert PITFALL not in _ids(art)


def test_fires_once_per_artifact():
    """Even with multiple deployment mentions, only one finding is emitted."""
    art = _plan("""
        ## Deployment

        Deploy the service. Deploy the worker. Ship the frontend.
        Production environment: AWS ECS.
    """)
    findings = _plan_missing_rollback(art, CATALOG)
    assert sum(1 for f in findings if f.pitfall_id == PITFALL) == 1
