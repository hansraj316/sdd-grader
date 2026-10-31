"""Tests for PLAN-MISSING-WEBHOOK-RELIABILITY pitfall.

Fires when a deployment plan mentions webhooks or event-callback delivery but has
no retry, idempotency, or signature-verification strategy.

Sources: Stripe webhook reliability guide; GitHub webhook security docs;
Twilio webhook delivery; Kiro production-readiness event-delivery gate;
ISO/IEC 25010:2023 §4.2.1 Reliability.
"""
from __future__ import annotations

import textwrap

from sddgrade.adapters.base import parse_sections
from sddgrade.catalog import load_catalog
from sddgrade.engine.lint import _plan_missing_webhook_reliability
from sddgrade.model import Artifact, ArtifactType

CATALOG = load_catalog()
PITFALL = "PLAN-MISSING-WEBHOOK-RELIABILITY"


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
    return [f.pitfall_id for f in _plan_missing_webhook_reliability(art, CATALOG)]


# ---------------------------------------------------------------------------
# Firing cases — webhook vocab present, no reliability strategy
# ---------------------------------------------------------------------------


def test_fires_webhook_no_retry():
    """Plan with webhook delivery but no retry strategy fires."""
    art = _plan("""
        # Deployment Plan

        ## Deploy

        Deploy the notification service to production on AWS ECS.

        ## Integrations

        The service sends a webhook to the customer's registered endpoint on
        every order status change.
    """)
    assert PITFALL in _ids(art)


def test_fires_webhook_endpoint_no_idempotency():
    """Plan with webhook endpoint but no idempotency fires."""
    art = _plan("""
        # Deployment Plan

        ## Production Release

        Ship the payment service to Kubernetes.

        ## Event Delivery

        Order events are pushed to the callback URL registered by the merchant.
    """)
    assert PITFALL in _ids(art)


def test_fires_event_callback_no_signature():
    """Plan with event callback but no signature verification fires."""
    art = _plan("""
        # Deployment Plan

        ## Deploy

        Deploy the integration hub to GKE.

        Third-party systems register an event callback to receive shipment updates.
    """)
    assert PITFALL in _ids(art)


def test_fires_event_subscription_no_reliability():
    """Plan with event subscription but no reliability strategy fires."""
    art = _plan("""
        # Deployment Plan

        ## Release

        Release the IoT data pipeline to production.

        Devices register an event subscription endpoint that receives telemetry alerts.
    """)
    assert PITFALL in _ids(art)


# ---------------------------------------------------------------------------
# Silent cases — reliability vocabulary present or trigger absent
# ---------------------------------------------------------------------------


def test_silent_retry_present():
    """Plan with webhook and retry strategy is silent."""
    art = _plan("""
        # Deployment Plan

        ## Deploy

        Deploy the notification service to production.

        ## Webhook Reliability

        Webhooks are delivered with exponential backoff retry (up to 5 attempts).
        Each delivery carries an idempotency key to prevent duplicate processing.
    """)
    assert PITFALL not in _ids(art)


def test_silent_idempotency_present():
    """Plan with webhook and idempotency strategy is silent."""
    art = _plan("""
        # Deployment Plan

        ## Production Release

        Ship the order service to ECS.

        The webhook payload includes an idempotent event ID. Receivers must
        deduplicate using this ID.
    """)
    assert PITFALL not in _ids(art)


def test_silent_hmac_signature_present():
    """Plan with webhook and HMAC signature is silent."""
    art = _plan("""
        # Deployment Plan

        ## Deploy

        Deploy the payment gateway integration to Kubernetes.

        Webhook endpoints are protected with HMAC-SHA256 signature verification
        using the shared webhook secret.
    """)
    assert PITFALL not in _ids(art)


def test_silent_at_least_once_delivery():
    """Plan with at-least-once delivery guarantee is silent."""
    art = _plan("""
        # Deployment Plan

        ## Deploy

        Deploy the event bus to production.

        Webhook dispatchers guarantee at-least-once delivery to registered endpoints.
    """)
    assert PITFALL not in _ids(art)


def test_silent_no_webhook_vocab():
    """Plan with no webhook vocabulary is silent."""
    art = _plan("""
        # Deployment Plan

        ## Deploy

        Deploy the analytics dashboard to production on ECS.

        ## Rollback

        Use blue-green deployment for instant rollback.
    """)
    assert PITFALL not in _ids(art)


def test_silent_no_deploy_guard():
    """Plan with webhook vocab but no deployment guard is silent."""
    art = _plan("""
        # Notes

        The service sends a webhook on order completion.
    """)
    assert PITFALL not in _ids(art)


def test_silent_webhook_in_fenced_block():
    """Webhook vocabulary inside a fenced code block does not trigger."""
    art = _plan("""
        # Deployment Plan

        ## Deploy

        Deploy the API gateway to production.

        ```yaml
        # webhook: https://example.com/callback
        replicas: 2
        ```

        ## Testing

        Run integration tests.
    """)
    assert PITFALL not in _ids(art)


def test_silent_webhook_in_heading():
    """Webhook vocabulary in a heading line does not trigger."""
    art = _plan("""
        # Deployment Plan

        ## Deploy

        Deploy the notification service to production on GKE.

        ## Webhook Configuration

        See the service mesh configuration for details.
    """)
    assert PITFALL not in _ids(art)


def test_silent_non_plan_artifact():
    """Non-plan artifacts (spec) are not checked."""
    art = _spec("""
        # Spec

        ## Requirements

        FR-001: The system shall send a webhook to the customer's registered endpoint.
    """)
    assert PITFALL not in _ids(art)


def test_silent_exponential_backoff_present():
    """Plan with webhook and exponential backoff is silent."""
    art = _plan("""
        # Deployment Plan

        ## Deploy

        Deploy the integration service to production on Kubernetes.

        The webhook dispatcher uses exponential backoff with a maximum of 10 retries
        before marking a delivery as failed.
    """)
    assert PITFALL not in _ids(art)
