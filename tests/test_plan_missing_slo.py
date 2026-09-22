"""Tests for PLAN-MISSING-SLO pitfall.

Fires when a plan.md with deployment vocabulary AND user-facing signals
(user/customer/client + service/API/endpoint/web/dashboard) has NO SLO vocabulary
(SLO, SLA, availability, uptime, error budget, p99, percentile, etc.).

Sources: Google SRE Book (SLOs as user contract), MAQA, ISO/IEC/IEEE 29148:2018 §5.2.3.
"""
from __future__ import annotations

import textwrap

from sddgrade.adapters.base import parse_sections
from sddgrade.catalog import load_catalog
from sddgrade.engine.lint import _plan_missing_slo
from sddgrade.model import Artifact, ArtifactType

CATALOG = load_catalog()
PITFALL = "PLAN-MISSING-SLO"


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
    return [f.pitfall_id for f in _plan_missing_slo(art, CATALOG)]


# ---------------------------------------------------------------------------
# Firing cases — user-facing plan, no SLO vocabulary
# ---------------------------------------------------------------------------


def test_fires_user_facing_service_no_slo():
    """Plan deploys a user-facing service with no SLO or availability target."""
    art = _plan("""
        ## Deployment Plan
        Deploy the dashboard service to production.
        Users will access the new reporting portal via HTTPS.
        The service runs on Kubernetes with 3 replicas.
        Deployment proceeds via rolling update.
    """)
    assert PITFALL in _ids(art)


def test_fires_customer_api_no_slo():
    """Plan exposes a customer-facing API endpoint with no reliability target."""
    art = _plan("""
        ## Release Plan
        Release the payment processing API to production.
        Customers will call the /payments endpoint to initiate transactions.
        Deploy with zero-downtime blue-green strategy.
        Monitoring dashboards will be updated post-deploy.
    """)
    assert PITFALL in _ids(art)


def test_fires_client_web_app_no_slo():
    """Plan launches a client-facing web app with no SLO."""
    art = _plan("""
        ## Deployment Plan
        Launch the client portal frontend to production.
        The web app is served via CloudFront CDN.
        Clients authenticate with OAuth2.
        Deploy during maintenance window 02:00–04:00 UTC.
    """)
    assert PITFALL in _ids(art)


def test_fires_user_dashboard_no_availability():
    """Plan deploys user-facing dashboard with no availability mention."""
    art = _plan("""
        ## Production Deployment
        Deploy the analytics dashboard for end users.
        The service connects to Postgres and Redis.
        Rolling deployment with canary 10% for first 30 minutes.
    """)
    assert PITFALL in _ids(art)


def test_fires_customer_service_no_error_budget():
    """Plan deploys customer-facing service, no error budget or p99 target."""
    art = _plan("""
        ## Deployment
        Deploy the customer notification service.
        Notifications are delivered to users via email and push.
        The service scales horizontally on demand.
        Alerts configured for pod restarts.
    """)
    assert PITFALL in _ids(art)


# ---------------------------------------------------------------------------
# Silent cases — SLO vocabulary present
# ---------------------------------------------------------------------------


def test_silent_when_slo_keyword_present():
    """Silent when 'SLO' appears in the plan."""
    art = _plan("""
        ## Deployment Plan
        Deploy the user-facing API service to production.
        SLO: 99.9% monthly availability, p99 latency ≤ 300 ms.
        Rolling deployment with health checks.
    """)
    assert PITFALL not in _ids(art)


def test_silent_when_availability_mentioned():
    """Silent when 'availability' appears."""
    art = _plan("""
        ## Production Deployment
        Deploy the dashboard service for users.
        Target availability: 99.95%.
        Deploy with canary release strategy.
    """)
    assert PITFALL not in _ids(art)


def test_silent_when_sla_mentioned():
    """Silent when 'SLA' appears."""
    art = _plan("""
        ## Release Plan
        Deploy the customer support API.
        SLA: 99.9% uptime guaranteed per contract.
        Rolling update with zero-downtime strategy.
    """)
    assert PITFALL not in _ids(art)


def test_silent_when_p99_mentioned():
    """Silent when 'p99' latency target is present."""
    art = _plan("""
        ## Deployment Plan
        Deploy the user portal to production.
        Latency target: p99 ≤ 200 ms under 1000 RPS.
        Blue-green deployment scheduled for next Tuesday.
    """)
    assert PITFALL not in _ids(art)


def test_silent_when_error_budget_mentioned():
    """Silent when 'error budget' vocabulary appears."""
    art = _plan("""
        ## Production Deployment
        Deploy the API gateway for all clients.
        Error budget: 0.1% monthly error rate.
        Alert on SLO breach within 5 minutes.
    """)
    assert PITFALL not in _ids(art)


def test_silent_when_uptime_mentioned():
    """Silent when 'uptime' target is stated."""
    art = _plan("""
        ## Deployment
        Deploy the customer-facing dashboard.
        Uptime target: 99.9% (< 44 minutes downtime/month).
        On-call escalation after 10 minutes of sustained degradation.
    """)
    assert PITFALL not in _ids(art)


# ---------------------------------------------------------------------------
# Silent cases — guard conditions not met
# ---------------------------------------------------------------------------


def test_silent_no_deploy_vocab():
    """Silent when no deployment vocabulary (not a deployment plan)."""
    art = _plan("""
        ## Architecture Overview
        The user-facing dashboard service will query the analytics API.
        Clients connect via REST.
        This document covers design only.
    """)
    assert PITFALL not in _ids(art)


def test_silent_no_user_signal():
    """Silent when no user-type actor (internal-only plan)."""
    art = _plan("""
        ## Deployment Plan
        Deploy the internal batch job processor to production.
        Rolling update with health check probe.
        No external service or API exposure.
        Deployment monitored via Datadog.
    """)
    assert PITFALL not in _ids(art)


def test_silent_spec_artifact():
    """Silent on spec artifact — plan-only check."""
    art = _spec("""
        ## Deployment Plan
        Deploy the user-facing dashboard service to production.
        The service handles customer requests via REST API.
        No reliability target is mentioned.
    """)
    assert PITFALL not in _ids(art)


def test_silent_fenced_block_only():
    """Silent when user/service vocab appear only in fenced code block."""
    art = _plan("""
        ## Deployment Plan
        Deploy the internal metrics collector to production.
        Rolling update with readiness probes.

        ```yaml
        # user-facing service customer dashboard
        replicas: 3
        ```
    """)
    assert PITFALL not in _ids(art)
