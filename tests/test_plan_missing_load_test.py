"""Tests for PLAN-MISSING-LOAD-TEST pitfall.

Fires when a deployment plan specifies performance-sensitive targets
(throughput, concurrent users, TPS/RPS, peak load) but has no
load-testing or performance-testing strategy.

Sources: Tessl spec-first deployment checklist, ISO 25010 §8.5
(Performance Efficiency testability), Kiro production-readiness gate.
"""
from __future__ import annotations

import textwrap

from sddgrade.adapters.base import parse_sections
from sddgrade.catalog import load_catalog
from sddgrade.engine.lint import _plan_missing_load_test
from sddgrade.model import Artifact, ArtifactType

CATALOG = load_catalog()
PITFALL = "PLAN-MISSING-LOAD-TEST"


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
    return [f.pitfall_id for f in _plan_missing_load_test(art, CATALOG)]


# ---------------------------------------------------------------------------
# Firing cases — performance targets with no load-test vocabulary
# ---------------------------------------------------------------------------


def test_fires_concurrent_users():
    """Plan with concurrent-users target and no load-test strategy."""
    art = _plan("""
        # Deployment Plan

        ## Deployment

        Deploy the API to production on AWS ECS.

        The service must support 10,000 concurrent users at peak hours.

        ## Testing

        Unit tests and integration tests are run before each deploy.
    """)
    assert PITFALL in _ids(art)


def test_fires_tps_target():
    """Plan citing TPS target with no load-test strategy fires."""
    art = _plan("""
        # Deployment Plan

        ## Release

        Ship the payment processing service to production.

        Target throughput: 5,000 TPS at peak load.

        ## Monitoring

        Datadog dashboards will track p99 latency.
    """)
    assert PITFALL in _ids(art)


def test_fires_requests_per_second():
    """Plan with requests-per-second target fires."""
    art = _plan("""
        # Deployment Plan

        ## Deploy

        Deploy the order service to Kubernetes.

        The API must handle 2,000 requests per second during flash sales.
    """)
    assert PITFALL in _ids(art)


def test_fires_high_volume():
    """Plan with high-volume signal fires."""
    art = _plan("""
        # Deployment Plan

        ## Deploy

        Deploy the notification service to production.

        The service must process high-volume traffic (peak: 50k messages/min).

        ## Rollback

        Use blue-green deployment for instant rollback.
    """)
    assert PITFALL in _ids(art)


def test_fires_peak_load():
    """Plan with peak-load signal but no load-test vocab fires."""
    art = _plan("""
        # Deployment Plan

        ## Production Release

        Release the search service to production.

        Peak load: 8,000 RPS during product launches.

        ## CI/CD

        Run unit tests and linting in CI before merge.
    """)
    assert PITFALL in _ids(art)


def test_fires_rps_target():
    """Plan with explicit RPS target fires."""
    art = _plan("""
        # Deployment Plan

        ## Deployment

        Deploy to GKE with 3 replicas.

        Throughput target: 1,500 RPS sustained, 3,000 RPS burst.
    """)
    assert PITFALL in _ids(art)


# ---------------------------------------------------------------------------
# Silent cases — load-test vocabulary present or trigger absent
# ---------------------------------------------------------------------------


def test_silent_load_test_k6():
    """Plan with k6 load testing mentioned is silent."""
    art = _plan("""
        # Deployment Plan

        ## Deploy

        Deploy to production. The service handles 5,000 concurrent users.

        ## Load Testing

        k6 script runs ramp-up from 0 to 5,000 VUs over 5 minutes.
        Thresholds: p95 < 200ms, error rate < 0.5%.
    """)
    assert PITFALL not in _ids(art)


def test_silent_load_test_jmeter():
    """Plan with JMeter load testing is silent."""
    art = _plan("""
        # Deployment Plan

        ## Deployment

        Deploy the checkout API. Peak load: 2,000 TPS.

        ## Performance Testing

        JMeter test plan runs 2-hour soak test before production deploy.
    """)
    assert PITFALL not in _ids(art)


def test_silent_load_test_gatling():
    """Plan mentioning Gatling is silent."""
    art = _plan("""
        # Deployment Plan

        ## Release

        Ship the recommendation engine. High traffic: 10,000 concurrent requests.

        Load test: Gatling simulation runs 30-minute steady-state scenario.
    """)
    assert PITFALL not in _ids(art)


def test_silent_load_test_locust():
    """Plan mentioning Locust is silent."""
    art = _plan("""
        # Deployment Plan

        ## Deploy

        Deploy to AWS ECS. Peak traffic: 1,000 RPS.

        Locust performance tests run in staging before each production deploy.
    """)
    assert PITFALL not in _ids(art)


def test_silent_load_test_benchmark():
    """Plan mentioning benchmark is silent."""
    art = _plan("""
        # Deployment Plan

        ## Production Deploy

        Deploy the caching layer. Throughput target: 500 requests per second.

        ## Performance

        Benchmarking runs nightly in the performance environment.
    """)
    assert PITFALL not in _ids(art)


def test_silent_stress_test():
    """Plan mentioning stress testing is silent."""
    art = _plan("""
        # Deployment Plan

        ## Release

        Deploy to production. Supports 5,000 concurrent connections.

        Stress testing confirms the service handles burst traffic.
    """)
    assert PITFALL not in _ids(art)


def test_silent_no_perf_sensitive_vocab():
    """Plan with no performance-sensitive vocabulary is silent."""
    art = _plan("""
        # Deployment Plan

        ## Deploy

        Deploy the admin dashboard to production.

        ## Testing

        Run unit tests and integration tests before deploy.

        ## Rollback

        Revert via blue-green swap.
    """)
    assert PITFALL not in _ids(art)


def test_silent_no_deploy_vocab():
    """Plan with perf vocab but no deploy guard is silent."""
    art = _plan("""
        # Notes

        The service handles 5,000 concurrent users.
    """)
    assert PITFALL not in _ids(art)


def test_silent_perf_vocab_in_fenced_block():
    """Performance-sensitive vocab inside a fenced code block does not trigger."""
    art = _plan("""
        # Deployment Plan

        ## Deploy

        Deploy the API to production.

        ```yaml
        # 5000 TPS target — configure autoscaling accordingly
        replicas: 10
        ```

        ## Testing

        Run integration tests.
    """)
    assert PITFALL not in _ids(art)


def test_silent_non_plan_artifact():
    """Non-plan artifacts (spec) are not checked."""
    art = _spec("""
        # Spec

        ## Requirements

        FR-001: The system shall handle high-volume traffic.

        The API must handle 5,000 concurrent users at peak.
    """)
    assert PITFALL not in _ids(art)


def test_silent_artillery():
    """Plan mentioning Artillery is silent."""
    art = _plan("""
        # Deployment Plan

        ## Deploy

        Deploy to production. High-traffic service: peak 3,000 RPS.

        Artillery load test runs before each release.
    """)
    assert PITFALL not in _ids(art)
