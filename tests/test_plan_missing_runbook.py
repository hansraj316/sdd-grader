"""Tests for PLAN-MISSING-RUNBOOK — deployment plans with no runbook or incident-response reference."""
from __future__ import annotations

import textwrap

from sddgrade.adapters.base import parse_sections
from sddgrade.catalog import load_catalog
from sddgrade.engine.lint import _plan_missing_runbook
from sddgrade.model import Artifact, ArtifactType

CATALOG = load_catalog()
PITFALL = "PLAN-MISSING-RUNBOOK"


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
    return [f.pitfall_id for f in _plan_missing_runbook(art, CATALOG)]


# ------------------------------------------------------------------ fires cases

def test_fires_on_deployment_section_no_runbook():
    """Plan has a Deployment section but no runbook mention."""
    art = _plan("""
        ## Deployment

        Deploy the service to production using Docker Compose.
        Set environment variables via secrets manager.
        Configure the health check at /health.
    """)
    assert PITFALL in _ids(art)


def test_fires_on_release_vocab_no_runbook():
    """Plan mentions 'release' but no runbook or on-call reference."""
    art = _plan("""
        ## Steps

        1. Build the Docker image.
        2. Push to ECR and release to ECS.
        3. Monitor dashboards after rollout.
    """)
    assert PITFALL in _ids(art)


def test_fires_on_production_vocab_no_incident_response():
    """Plan mentions 'production' with no incident-response vocabulary."""
    art = _plan("""
        ## Architecture

        The service will be deployed to production on AWS ECS.
        Observability: metrics and logs are forwarded to Datadog.
    """)
    assert PITFALL in _ids(art)


def test_fires_on_staging_deploy_no_runbook():
    """Plan mentions staging deployment with no runbook."""
    art = _plan("""
        ## Deployment

        Ship the build to staging, then promote to production after QA sign-off.
        Use zero-downtime blue/green strategy.
    """)
    assert PITFALL in _ids(art)


def test_fires_on_deploy_no_escalation_path():
    """Kubernetes plan with no escalation or on-call reference."""
    art = _plan("""
        ## Release Plan

        Deploy the new image via `kubectl rollout deploy/myapp`.
        Rolling update with maxUnavailable=0.
        Rollback: kubectl rollout undo deploy/myapp.
    """)
    assert PITFALL in _ids(art)


def test_fires_on_ship_verb_no_runbook():
    """Plan uses 'ship' vocabulary with no incident-response reference."""
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


def test_silent_when_runbook_mentioned():
    """Plan mentions 'runbook' explicitly."""
    art = _plan("""
        ## Deployment

        Deploy to production on ECS.
        See the on-call runbook at docs/runbooks/task-export-service.md.
    """)
    assert PITFALL not in _ids(art)


def test_silent_when_playbook_mentioned():
    """Plan mentions 'playbook'."""
    art = _plan("""
        ## Release

        Deploy to production Kubernetes cluster.
        Follow the deployment playbook for go-live verification steps.
    """)
    assert PITFALL not in _ids(art)


def test_silent_when_on_call_mentioned():
    """Plan mentions 'on-call'."""
    art = _plan("""
        ## Deployment

        Ship to staging then production.
        Escalation path: on-call engineer → SRE team lead.
    """)
    assert PITFALL not in _ids(art)


def test_silent_when_incident_response_mentioned():
    """Plan mentions 'incident response'."""
    art = _plan("""
        ## Production Deployment

        Deploy service to production on AWS EKS.
        Incident response: page the on-call via PagerDuty alert rule 'task-export-slo'.
    """)
    assert PITFALL not in _ids(art)


def test_silent_when_oncall_no_hyphen():
    """Plan mentions 'oncall' (no hyphen variant)."""
    art = _plan("""
        ## Release

        Release to production after smoke tests pass.
        Alert the oncall engineer if error rate exceeds 1% within 5 minutes.
    """)
    assert PITFALL not in _ids(art)


def test_silent_when_escalation_procedure_mentioned():
    """Plan mentions 'escalation path'."""
    art = _plan("""
        ## Deployment

        Deploy to production on ECS.
        Escalation path: Tier-1 → SRE → service owner.
    """)
    assert PITFALL not in _ids(art)


def test_silent_when_ops_guide_mentioned():
    """Plan mentions 'ops guide'."""
    art = _plan("""
        ## Production Release

        Ship the updated service to production.
        See the ops guide for post-deploy verification steps.
    """)
    assert PITFALL not in _ids(art)


def test_silent_on_spec_artifact():
    """Check does not fire on spec artifacts."""
    raw = textwrap.dedent("""
        ## Deployment

        Deploy to production with no runbook mentioned.
    """).strip()
    spec = Artifact(
        path="spec.md",
        type=ArtifactType.SPEC,
        feature_id="test",
        raw=raw,
        sections=parse_sections(raw),
    )
    assert PITFALL not in [f.pitfall_id for f in _plan_missing_runbook(spec, CATALOG)]
