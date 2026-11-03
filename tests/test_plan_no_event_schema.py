"""Tests for PLAN-NO-EVENT-SCHEMA pitfall.

Fires when a deployment plan references event-driven messaging vocabulary
(Kafka, RabbitMQ, SQS, SNS, NATS, EventBridge, message queue, event bus, …)
but contains no event schema or contract strategy (AsyncAPI, CloudEvents,
schema registry, Avro, message schema, …).

Sources: AsyncAPI specification (asyncapi.com); CloudEvents (cloudevents.io);
Confluent Schema Registry; Kiro production-readiness service-contract gate;
Tessl contract-first event design; ISO/IEC 25010:2023 Interoperability.
"""
from __future__ import annotations

import textwrap

from sddgrade.adapters.base import parse_sections
from sddgrade.catalog import load_catalog
from sddgrade.engine.lint import _plan_no_event_schema
from sddgrade.model import Artifact, ArtifactType

CATALOG = load_catalog()
PITFALL = "PLAN-NO-EVENT-SCHEMA"


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
    return [f.pitfall_id for f in _plan_no_event_schema(art, CATALOG)]


# ---------------------------------------------------------------------------
# FIRE cases — event-bus vocab present, no schema strategy
# ---------------------------------------------------------------------------


def test_fires_kafka_no_schema():
    """Plan with Kafka topic but no event schema fires."""
    art = _plan("""
        # Deployment Plan

        ## Deploy to Production

        The service publishes domain events to a Kafka topic for downstream consumers.
        Consumers subscribe to the topic and process events asynchronously.
    """)
    assert PITFALL in _ids(art)


def test_fires_rabbitmq_no_schema():
    """Plan with RabbitMQ but no event schema fires."""
    art = _plan("""
        # Deployment Plan

        ## Deployment

        Deploy the service to production using Docker.
        Messages are pushed to a RabbitMQ exchange and routed to consumer queues.
    """)
    assert PITFALL in _ids(art)


def test_fires_sqs_no_schema():
    """Plan with SQS queue but no event schema fires."""
    art = _plan("""
        # Deployment Plan

        ## Deployment Steps

        1. Deploy the order service to ECS.
        2. Order events are placed onto an SQS queue for the fulfillment service.
        3. The fulfillment service polls the queue every 5 seconds.
    """)
    assert PITFALL in _ids(art)


def test_fires_event_bus_no_schema():
    """Plan with generic event bus but no event schema fires."""
    art = _plan("""
        # Deployment Plan

        ## Production Deployment

        All domain events flow through a shared event bus to decouple producers.
        Each service subscribes to the events it needs.
    """)
    assert PITFALL in _ids(art)


def test_fires_message_queue_no_schema():
    """Plan with message queue but no schema fires."""
    art = _plan("""
        # Deployment Plan

        ## Deploy

        Ship the notification service to production.
        Notifications are queued in a message queue and consumed by the notification service.
    """)
    assert PITFALL in _ids(art)


# ---------------------------------------------------------------------------
# SILENT cases — event-bus vocab present AND schema strategy present
# ---------------------------------------------------------------------------


def test_silent_kafka_with_asyncapi():
    """Kafka with AsyncAPI specification is silent."""
    art = _plan("""
        # Deployment Plan

        ## Deploy to Production

        The service publishes domain events to a Kafka topic.
        All event channels are described in the AsyncAPI specification at docs/asyncapi.yaml.
    """)
    assert PITFALL not in _ids(art)


def test_silent_kafka_with_schema_registry():
    """Kafka with schema registry is silent."""
    art = _plan("""
        # Deployment Plan

        ## Deployment

        Deploy the service to production.
        Events are published to Kafka topics with schemas registered in the schema registry.
        All producers validate against the registered schema before publishing.
    """)
    assert PITFALL not in _ids(art)


def test_silent_sqs_with_cloudevents():
    """SQS with CloudEvents envelope is silent."""
    art = _plan("""
        # Deployment Plan

        ## Deployment Steps

        Deploy the service.
        Messages are placed on an SQS queue using the CloudEvents envelope format.
        Consumers parse the CloudEvents payload to extract event type and data.
    """)
    assert PITFALL not in _ids(art)


def test_silent_event_bus_with_event_schema():
    """Event bus with explicit event schema reference is silent."""
    art = _plan("""
        # Deployment Plan

        ## Production Deployment

        Deploy the microservices to Kubernetes.
        All events on the event bus conform to the event schema defined in events/schema.json.
    """)
    assert PITFALL not in _ids(art)


def test_silent_rabbitmq_with_message_schema():
    """RabbitMQ with message schema is silent."""
    art = _plan("""
        # Deployment Plan

        ## Deploy

        Deploy using Docker Compose.
        RabbitMQ messages follow the message schema documented in docs/events.md.
    """)
    assert PITFALL not in _ids(art)


def test_silent_no_deploy_vocab():
    """Plan without deploy vocabulary is silent (deploy guard not passed)."""
    art = _plan("""
        # Architecture Overview

        Kafka is the backbone of our event-driven system.
        We have not defined an event schema yet.
    """)
    assert PITFALL not in _ids(art)


def test_silent_kafka_only_in_fenced_block():
    """Kafka only inside a fenced code block is silent."""
    art = _plan("""
        # Deployment Plan

        ## Deploy to Production

        Deploy the REST service (no event-driven components).

        ```bash
        kafka-topics.sh --create --topic my-topic
        ```
    """)
    assert PITFALL not in _ids(art)


def test_silent_no_messaging_vocab():
    """Plan with no messaging vocabulary is silent."""
    art = _plan("""
        # Deployment Plan

        ## Deployment

        Deploy the service to production.
        The service exposes a REST API backed by PostgreSQL.
        All communication is synchronous HTTP with no async components.
    """)
    assert PITFALL not in _ids(art)


def test_silent_kafka_with_avro():
    """Kafka with Avro schema is silent."""
    art = _plan("""
        # Deployment Plan

        ## Deploy to Production

        Deploy the analytics pipeline to production.
        Events published to Kafka topics use Avro schemas stored in the schema registry.
    """)
    assert PITFALL not in _ids(art)


def test_silent_eventbridge_with_json_schema():
    """EventBridge with JSON schema is silent."""
    art = _plan("""
        # Deployment Plan

        ## Production Deployment

        Deploy Lambda functions to production.
        Events are published to EventBridge with a JSON schema for each event type.
        Consumer Lambdas validate the incoming JSON schema before processing.
    """)
    assert PITFALL not in _ids(art)
