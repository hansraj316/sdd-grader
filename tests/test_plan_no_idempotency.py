"""Tests for PLAN-NO-IDEMPOTENCY pitfall.

Fires when a plan.md with deployment vocabulary AND retry/reprocess/at-least-once
semantics has no idempotency guarantee (idempotent/exactly-once/deduplication/dedupe/
unique constraint/conditional write) anywhere in the document.

Sources: Amazon Kiro production-readiness gate; Tessl spec-first;
         ISO/IEC 25010:2011 §4.2.1.2 Fault Tolerance;
         Twelve-Factor App (stateless, retry-safe processes).
"""
from __future__ import annotations

import textwrap

from sddgrade.adapters.base import parse_sections
from sddgrade.catalog import load_catalog
from sddgrade.engine.lint import _plan_no_idempotency
from sddgrade.model import Artifact, ArtifactType

CATALOG = load_catalog()
PITFALL = "PLAN-NO-IDEMPOTENCY"


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
    return [f.pitfall_id for f in _plan_no_idempotency(art, CATALOG)]


# ---------------------------------------------------------------------------
# Firing cases — retry vocab present, no idempotency silence token
# ---------------------------------------------------------------------------

def test_fires_retry_no_idempotency():
    """Plan mentions retry with exponential backoff but no safety guarantee mentioned."""
    art = _plan("""
        ## Deployment Plan
        We will deploy the payment service to production.
        The service will retry failed requests with exponential backoff up to 3 times.
        No safety strategy is defined for repeated operations.
    """)
    assert PITFALL in _ids(art)


def test_fires_retries_no_deduplication():
    """Plan references retries (plural) with no replay safety mentioned."""
    art = _plan("""
        ## Release Plan
        Deploy the notification service to production environment.
        The worker performs retries on failed email delivery attempts.
        No replay safety mechanism is specified in this plan.
    """)
    assert PITFALL in _ids(art)


def test_fires_reprocessed_no_safety():
    """Plan describes reprocessed jobs (past-tense form) with no safety strategy."""
    art = _plan("""
        ## Deployment
        Release the batch processing service to staging and production.
        Failed jobs will be reprocessed automatically after a delay.
        No operation-safety strategy is mentioned.
    """)
    assert PITFALL in _ids(art)


def test_fires_at_least_once_delivery():
    """Plan specifies at-least-once delivery semantics with no compensation."""
    art = _plan("""
        ## Production Release
        Deploy the event pipeline to production.
        The Kafka consumer is configured for at-least-once delivery semantics.
    """)
    assert PITFALL in _ids(art)


def test_fires_requeue_no_idempotency():
    """Plan mentions requeue strategy with no idempotency guarantee."""
    art = _plan("""
        ## Deployment Plan
        Deploy the order processing service to production.
        Failed orders are requeued to the SQS dead-letter queue for retry.
    """)
    # Note: 'dead-letter queue' is a DLQ concept, not an idempotency guarantee.
    assert PITFALL in _ids(art)


def test_fires_replay_no_exactly_once():
    """Plan describes event replay with no exactly-once or deduplication mention."""
    art = _plan("""
        ## Release Notes
        Deploy the event sourcing service.
        Consumers support replay of historical events from Kafka.
    """)
    assert PITFALL in _ids(art)


def test_fires_backoff_no_idempotency():
    """Plan specifies backoff for retries but no safety guarantee."""
    art = _plan("""
        ## Staging Deployment
        Deploy the API gateway with the new retry policy.
        The upstream client uses backoff with jitter on 5xx errors.
    """)
    assert PITFALL in _ids(art)


# ---------------------------------------------------------------------------
# Silent cases — idempotency silence token present
# ---------------------------------------------------------------------------

def test_silent_idempotent_keyword():
    """Plan states all operations are idempotent — silenced."""
    art = _plan("""
        ## Deployment Plan
        Deploy the payment service to production.
        The service will retry failed requests with exponential backoff.
        All payment operations are idempotent: duplicate retries produce no additional charges.
    """)
    assert PITFALL not in _ids(art)


def test_silent_exactly_once_semantics():
    """Plan specifies exactly-once Kafka producer semantics — silenced."""
    art = _plan("""
        ## Production Release
        Deploy the event pipeline to production.
        The Kafka consumer is configured for at-least-once delivery.
        The Kafka producer is configured for exactly-once semantics.
    """)
    assert PITFALL not in _ids(art)


def test_silent_deduplication_strategy():
    """Plan describes a deduplication strategy — silenced."""
    art = _plan("""
        ## Deployment Plan
        Deploy the notification service to production environment.
        The worker retries failed notifications.
        A deduplication key prevents sending the same notification twice.
    """)
    assert PITFALL not in _ids(art)


def test_silent_dedupe_keyword():
    """Plan uses 'dedupe' (short form) — silenced."""
    art = _plan("""
        ## Release Plan
        Deploy the order service to production.
        Failed orders are retried automatically.
        We dedupe orders by order_id to prevent double-processing.
    """)
    assert PITFALL not in _ids(art)


def test_silent_unique_constraint():
    """Plan relies on a unique constraint for idempotency — silenced."""
    art = _plan("""
        ## Deployment Plan
        Deploy the payment service to production.
        Failed payments are resubmitted with the same idempotency key.
        The database enforces a unique constraint on (idempotency_key, account_id).
    """)
    assert PITFALL not in _ids(art)


def test_silent_conditional_write():
    """Plan uses conditional writes for retry safety — silenced."""
    art = _plan("""
        ## Production Deployment
        Deploy the inventory service to production.
        The service uses backoff on transient failures.
        All updates use a conditional write with the current ETag to prevent duplicate mutations.
    """)
    assert PITFALL not in _ids(art)


def test_silent_no_retry_vocab():
    """Plan has deployment vocab but no retry/reprocess vocabulary — not applicable."""
    art = _plan("""
        ## Deployment Plan
        Deploy the frontend to production via CDN.
        No error recovery logic is present in this release.
    """)
    assert PITFALL not in _ids(art)


def test_silent_no_deploy_vocab():
    """Plan has retry vocab but no deployment section or vocab — guard prevents false positive."""
    art = _plan("""
        ## Technical Notes
        Consider using retry logic in the client SDK with exponential backoff.
        This is a developer guide with general engineering patterns only.
    """)
    assert PITFALL not in _ids(art)


def test_silent_spec_artifact():
    """Check does not apply to spec artifacts — skipped."""
    art = _spec("""
        ## Deployment Plan
        Deploy the service to production.
        The system shall retry failed requests with exponential backoff.
    """)
    assert PITFALL not in _ids(art)


def test_silent_fenced_retry_only():
    """Retry vocab only appears inside a fenced code block — not a trigger."""
    art = _plan("""
        ## Deployment Plan
        Deploy the service to production.

        ```python
        for attempt in range(3):
            try:
                send_payment()
            except Exception:
                retry(attempt)
        ```

        All operations use idempotent writes; the fenced block above is illustrative only.
    """)
    assert PITFALL not in _ids(art)
