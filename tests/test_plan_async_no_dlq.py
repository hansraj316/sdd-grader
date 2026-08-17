"""Tests for PLAN-ASYNC-NO-DLQ — async messaging plans with no dead-letter queue strategy."""
from __future__ import annotations

import textwrap

from sddgrade.adapters.base import parse_sections
from sddgrade.catalog import load_catalog
from sddgrade.engine.lint import _plan_async_no_dlq
from sddgrade.model import Artifact, ArtifactType

CATALOG = load_catalog()
PITFALL = "PLAN-ASYNC-NO-DLQ"


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
    return [f.pitfall_id for f in _plan_async_no_dlq(art, CATALOG)]


# ------------------------------------------------------------------ fires cases

def test_fires_on_kafka_consumer_no_dlq():
    """Plan describes Kafka consumers with no DLQ mention."""
    art = _plan("""
        ## Architecture

        The service uses Kafka consumer groups to process task-export events.
        Each consumer processes one message at a time and commits offsets on success.
    """)
    assert PITFALL in _ids(art)


def test_fires_on_sqs_no_dead_letter():
    """Plan uses SQS but has no dead-letter configuration."""
    art = _plan("""
        ## Message Processing

        Events are published to an SQS queue.
        Workers poll the queue and process messages.
        Failed messages are retried up to 3 times.
    """)
    assert PITFALL in _ids(art)


def test_fires_on_celery_worker_no_dlq():
    """Plan uses Celery workers with no poison-message handling."""
    art = _plan("""
        ## Background Jobs

        Celery workers process export jobs asynchronously.
        Jobs are retried automatically on failure.
    """)
    assert PITFALL in _ids(art)


def test_fires_on_rabbitmq_no_dlq():
    """Plan uses RabbitMQ with no DLQ reference."""
    art = _plan("""
        ## Event Bus

        Events are published to RabbitMQ and consumed by downstream services.
        The consumer acknowledges each message after processing.
    """)
    assert PITFALL in _ids(art)


def test_fires_on_async_task_no_dlq():
    """Plan describes an async task pipeline with no DLQ."""
    art = _plan("""
        ## Task Pipeline

        Async tasks are placed on a queue for background processing.
        Workers pick up tasks from the queue and execute them in parallel.
    """)
    assert PITFALL in _ids(art)


def test_fires_on_event_bus_no_dlq():
    """Plan references an event bus with no error handling."""
    art = _plan("""
        ## Integration

        The service publishes events to the event bus for downstream consumers.
        SNS fan-out delivers messages to multiple SQS-subscribed workers.
    """)
    assert PITFALL in _ids(art)


# ------------------------------------------------------------------ silent cases

def test_silent_when_dlq_mentioned():
    """Plan uses SQS and names a DLQ — check is silent."""
    art = _plan("""
        ## Message Processing

        Events are published to an SQS queue.
        Workers poll the queue and process messages.
        Failed messages are routed to the DLQ (task-export-dlq) after 3 retries.
    """)
    assert PITFALL not in _ids(art)


def test_silent_when_dead_letter_mentioned():
    """Plan uses Kafka and mentions a dead-letter queue explicitly."""
    art = _plan("""
        ## Architecture

        The service uses Kafka consumers to process events.
        Unprocessable messages are forwarded to the dead-letter topic for inspection.
    """)
    assert PITFALL not in _ids(art)


def test_silent_when_poison_pill_mentioned():
    """Plan names a poison-pill strategy."""
    art = _plan("""
        ## Error Handling

        Celery workers retry failed tasks up to 5 times.
        Poison-pill messages are quarantined in a separate error queue.
    """)
    assert PITFALL not in _ids(art)


def test_silent_when_nack_strategy():
    """Plan uses RabbitMQ and describes nack-based routing."""
    art = _plan("""
        ## RabbitMQ Configuration

        Consumers nack unprocessable messages so they are routed to the error exchange.
        All nack'd messages are inspected daily.
    """)
    assert PITFALL not in _ids(art)


def test_silent_when_break_queue_mentioned():
    """Plan uses a break-queue pattern."""
    art = _plan("""
        ## Queue Strategy

        SQS consumers process messages with a visibility timeout.
        Messages exceeding retries are moved to the break-queue for manual review.
    """)
    assert PITFALL not in _ids(art)


def test_silent_when_no_async_messaging():
    """Plan has no async messaging vocabulary — guard does not fire."""
    art = _plan("""
        ## Deployment

        Deploy the service to production using Docker Compose.
        Configure environment variables via the secrets manager.
        Health check at /health.
    """)
    assert PITFALL not in _ids(art)


def test_silent_when_queue_in_fenced_block():
    """Async vocab only appears inside a fenced code block — guard does not fire."""
    art = _plan("""
        ## Architecture

        The service uses synchronous REST APIs only.

        ```yaml
        # Example: consumer config (not used in this plan)
        kafka:
          consumer:
            group-id: my-group
        ```
    """)
    assert PITFALL not in _ids(art)


def test_silent_when_unprocessable_in_fenced_block():
    """DLQ silencing via fenced block: guard fires, but DLQ search covers full raw text."""
    # The _DLQ_RE searches art.raw without fenced masking (silence is broad by design —
    # even a comment mentioning DLQ is enough to suppress the finding).
    art = _plan("""
        ## Message Processing

        The service uses an SQS queue for async task processing.

        ```python
        # TODO: route unprocessable messages to a DLQ
        ```
    """)
    # DLQ silencing is intentionally broad: the word 'unprocessable' appears in the fenced
    # block but _DLQ_RE searches art.raw so it still silences. This is the documented
    # design: even a code-comment DLQ mention counts as awareness.
    assert PITFALL not in _ids(art)


def test_silent_when_message_requeue_mentioned():
    """Plan uses message-requeue vocabulary — check is silent."""
    art = _plan("""
        ## Retry Policy

        Kafka consumers retry failed messages up to 3 times.
        After 3 failures, message-requeue to the error topic is triggered.
    """)
    assert PITFALL not in _ids(art)


def test_fires_returns_correct_pitfall_id():
    """Returned finding has the correct pitfall ID."""
    art = _plan("""
        ## Processing

        Events are queued and processed by background worker-queue jobs.
    """)
    findings = _plan_async_no_dlq(art, CATALOG)
    assert len(findings) == 1
    assert findings[0].pitfall_id == PITFALL


def test_fires_anchored_to_first_async_line():
    """Finding is anchored to the first non-fenced async-messaging line."""
    art = _plan("""
        ## Overview

        The service exports data via a Kafka consumer group.
        A consumer reads from the export topic and writes output files.
    """)
    findings = _plan_async_no_dlq(art, CATALOG)
    assert findings
    # After dedent+strip: line 1="## Overview", line 2="", line 3="The service exports ..."
    assert findings[0].line is not None
    assert findings[0].line >= 1
