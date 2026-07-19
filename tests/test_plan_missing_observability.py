"""Tests for PLAN-MISSING-OBSERVABILITY — deployment plans missing an observability strategy."""
from __future__ import annotations

import textwrap

from sddgrade.adapters.base import parse_sections
from sddgrade.catalog import load_catalog
from sddgrade.engine.lint import _plan_missing_observability
from sddgrade.model import Artifact, ArtifactType

CATALOG = load_catalog()
PITFALL = "PLAN-MISSING-OBSERVABILITY"


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
    return [f.pitfall_id for f in _plan_missing_observability(art, CATALOG)]


# ------------------------------------------------------------------ fires cases

def test_fires_on_deploy_section_no_observability():
    """Plan has a Deployment section but no observability mention."""
    art = _plan("""
        ## Deployment

        Run `kubectl apply -f manifests/api.yaml` to deploy the new image.
        Verify health endpoint returns 200.
    """)
    assert PITFALL in _ids(art)


def test_fires_on_deploy_vocab_no_observability():
    """Plan uses 'deploy' keyword in prose but never mentions observability."""
    art = _plan("""
        ## Steps

        1. Deploy the service to production using the CI pipeline.
        2. Verify health check endpoint returns 200.
        3. Run smoke tests.
    """)
    assert PITFALL in _ids(art)


def test_fires_on_production_vocab_no_observability():
    """Plan mentions 'production' but has no monitoring/logging."""
    art = _plan("""
        ## Release

        The feature will ship to production on Friday.
        Run the migration script before deploying.
    """)
    assert PITFALL in _ids(art)


def test_fires_on_ship_keyword():
    """Plan says 'shipping' but no observability vocab."""
    art = _plan("""
        ## Steps

        1. Shipping to staging first, then production.
        2. Confirm rollback procedure is ready.
    """)
    assert PITFALL in _ids(art)


def test_message_content():
    """Finding message references monitoring/logging/metrics/alerting."""
    art = _plan("""
        ## Deployment

        Deploy via helm upgrade.
    """)
    findings = _plan_missing_observability(art, CATALOG)
    assert findings
    assert "observability" in findings[0].message.lower() or "monitor" in findings[0].message.lower()


# ------------------------------------------------------------------ silent cases

def test_silent_on_monitoring_keyword():
    """Plan with 'monitoring' present should not fire."""
    art = _plan("""
        ## Deployment

        Deploy to production. Set up monitoring dashboards in Datadog.
    """)
    assert _ids(art) == []


def test_silent_on_logging_keyword():
    """Plan with 'logging' present should not fire."""
    art = _plan("""
        ## Deployment

        Deploy the service. Configure logging to ship to Splunk.
    """)
    assert _ids(art) == []


def test_silent_on_metrics_keyword():
    """Plan with 'metrics' present should not fire."""
    art = _plan("""
        ## Release

        Ship to production. Emit Prometheus metrics for latency and error rate.
    """)
    assert _ids(art) == []


def test_silent_on_alerting_keyword():
    """Plan with 'alerting' present should not fire."""
    art = _plan("""
        ## Deployment

        Deploy and configure alerting rules for p95 > 500ms.
    """)
    assert _ids(art) == []


def test_silent_on_slo_keyword():
    """Plan that mentions SLO should not fire."""
    art = _plan("""
        ## Deployment

        Ship to production. The SLO for this service is 99.9% uptime.
    """)
    assert _ids(art) == []


def test_silent_on_tracing_keyword():
    """Plan that mentions tracing should not fire."""
    art = _plan("""
        ## Deployment

        Deploy to production. Enable distributed tracing via Jaeger.
    """)
    assert _ids(art) == []


def test_silent_on_pure_refactor_plan():
    """Refactoring plan with no deployment vocab — guard should prevent firing."""
    art = _plan("""
        ## Steps

        1. Rename the `UserService` class to `AccountService`.
        2. Update all import references.
        3. Run unit tests to confirm nothing broke.
    """)
    assert _ids(art) == []


def test_fires_exactly_once():
    """Finding should fire at most once per artifact even with multiple deploy sections."""
    art = _plan("""
        ## Deployment to Staging

        Run `helm upgrade --install`.

        ## Deployment to Production

        Promote the staging image.
    """)
    ids = _ids(art)
    assert ids.count(PITFALL) == 1


def test_silent_on_spec_artifact():
    """Check only applies to plan.md; spec artifacts should not fire."""
    art = _spec("""
        ## Deployment

        The service will deploy to production. No observability mentioned.
    """)
    assert _ids(art) == []
