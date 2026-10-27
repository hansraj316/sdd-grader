"""Tests for PLAN-MISSING-CIRCUIT-BREAKER pitfall.

Fires when a deployment plan mentions retry or timeout strategies but has
no circuit-breaker or fault-isolation vocabulary.

Sources: Netflix Hystrix; Resilience4j; CNCF Resilience Trail Map;
Kiro production-readiness gate; ISO/IEC 25010:2011 §4.2.1.2 Fault Tolerance.
"""
from __future__ import annotations

import textwrap

from sddgrade.adapters.base import parse_sections
from sddgrade.catalog import load_catalog
from sddgrade.engine.lint import _plan_missing_circuit_breaker
from sddgrade.model import Artifact, ArtifactType

CATALOG = load_catalog()
PITFALL = "PLAN-MISSING-CIRCUIT-BREAKER"


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
    return [f.pitfall_id for f in _plan_missing_circuit_breaker(art, CATALOG)]


# ---------------------------------------------------------------------------
# Firing cases — retry/timeout vocab present, no circuit-breaker
# ---------------------------------------------------------------------------


def test_fires_retry_no_circuit_breaker():
    """Plan with retry strategy but no circuit-breaker fires."""
    art = _plan("""
        # Deployment Plan

        ## Deploy

        Deploy the payment service to production on Kubernetes.

        ## Resilience

        Calls to the payment gateway use retry with exponential backoff (3 attempts).
    """)
    assert PITFALL in _ids(art)


def test_fires_timeout_no_circuit_breaker():
    """Plan with timeout strategy but no circuit-breaker fires."""
    art = _plan("""
        # Deployment Plan

        ## Production Release

        Ship the order service to AWS ECS.

        ## Error Handling

        All outbound HTTP calls have a 5-second timeout to prevent hanging threads.
    """)
    assert PITFALL in _ids(art)


def test_fires_backoff_no_circuit_breaker():
    """Plan with backoff vocabulary but no circuit-breaker fires."""
    art = _plan("""
        # Deployment Plan

        ## Deploy

        Deploy the notification service to GKE.

        The SMS gateway integration uses exponential backoff on transient errors.
    """)
    assert PITFALL in _ids(art)


def test_fires_max_attempts_no_circuit_breaker():
    """Plan with max attempts vocabulary but no circuit-breaker fires."""
    art = _plan("""
        # Deployment Plan

        ## Release

        Deploy the webhook dispatcher to production.

        Webhook delivery uses max attempts of 5 with 10-second intervals.
    """)
    assert PITFALL in _ids(art)


def test_fires_retry_policy_no_circuit_breaker():
    """Plan with retry policy vocabulary but no circuit-breaker fires."""
    art = _plan("""
        # Deployment Plan

        ## Deploy

        Deploy the analytics ingestion service to production.

        The Kafka consumer applies a retry policy with 3 retries on deserialization errors.
    """)
    assert PITFALL in _ids(art)


# ---------------------------------------------------------------------------
# Silent cases — circuit-breaker vocabulary present or trigger absent
# ---------------------------------------------------------------------------


def test_silent_circuit_breaker_present():
    """Plan with circuit-breaker mention is silent."""
    art = _plan("""
        # Deployment Plan

        ## Deploy

        Deploy the payment service to production.

        ## Resilience

        Calls to the gateway use retry with exponential backoff (3 attempts).
        A circuit breaker trips after 5 consecutive failures and resets after 30 seconds.
    """)
    assert PITFALL not in _ids(art)


def test_silent_resilience4j():
    """Plan mentioning Resilience4j is silent."""
    art = _plan("""
        # Deployment Plan

        ## Production Release

        Ship the order service to Kubernetes.

        Outbound calls use a 5-second timeout. Resilience4j manages fault isolation.
    """)
    assert PITFALL not in _ids(art)


def test_silent_hystrix():
    """Plan mentioning Hystrix is silent."""
    art = _plan("""
        # Deployment Plan

        ## Deploy

        Deploy to AWS ECS.

        The legacy gateway integration uses Hystrix for circuit breaking and retry.
    """)
    assert PITFALL not in _ids(art)


def test_silent_polly():
    """Plan mentioning Polly is silent."""
    art = _plan("""
        # Deployment Plan

        ## Release

        Deploy the .NET service to Azure Container Apps.

        All HTTP client calls use Polly policies: retry 3 times with backoff.
    """)
    assert PITFALL not in _ids(art)


def test_silent_bulkhead():
    """Plan mentioning bulkhead is silent."""
    art = _plan("""
        # Deployment Plan

        ## Deploy

        Deploy the API gateway. Calls to the inventory service retry on 503.

        Bulkhead isolation prevents thread exhaustion per upstream.
    """)
    assert PITFALL not in _ids(art)


def test_silent_no_retry_vocab():
    """Plan with no retry or timeout vocabulary is silent."""
    art = _plan("""
        # Deployment Plan

        ## Deploy

        Deploy the admin dashboard to production on AWS ECS.

        ## Rollback

        Use blue-green deployment for instant rollback.
    """)
    assert PITFALL not in _ids(art)


def test_silent_no_deploy_guard():
    """Plan with retry vocab but no deployment guard is silent."""
    art = _plan("""
        # Notes

        The service uses retry with backoff.
    """)
    assert PITFALL not in _ids(art)


def test_silent_retry_in_fenced_block():
    """Retry vocabulary inside a fenced code block does not trigger."""
    art = _plan("""
        # Deployment Plan

        ## Deploy

        Deploy the API to production.

        ```yaml
        # retry: 3
        # timeout: 5s
        replicas: 2
        ```

        ## Testing

        Run integration tests.
    """)
    assert PITFALL not in _ids(art)


def test_silent_retry_in_heading():
    """Retry vocabulary in a heading line does not trigger."""
    art = _plan("""
        # Deployment Plan

        ## Deploy

        Deploy the notification service to production on GKE.

        ## Retry and Timeout Policies

        See the service mesh configuration for details.
    """)
    assert PITFALL not in _ids(art)


def test_silent_non_plan_artifact():
    """Non-plan artifacts (spec) are not checked."""
    art = _spec("""
        # Spec

        ## Requirements

        FR-001: The system shall retry failed requests up to 3 times with backoff.
    """)
    assert PITFALL not in _ids(art)
