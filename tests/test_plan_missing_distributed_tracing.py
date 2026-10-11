"""Tests for PLAN-MISSING-DISTRIBUTED-TRACING pitfall.

Fires when a plan.md with deployment vocabulary AND microservices/service-mesh
vocabulary (microservice, service mesh, api gateway, inter-service, Istio, Envoy,
Linkerd, distributed system, multiple services) has no distributed-tracing strategy
(OpenTelemetry, OTEL, Jaeger, Zipkin, X-Ray, trace_id, correlation_id, etc.)
anywhere in the non-fenced text.

Source: Kiro production-readiness gate (distributed tracing for multi-service),
        CNCF Cloud Native Trail Map — Observability,
        OpenTelemetry CNCF graduated project.
"""
from __future__ import annotations

import textwrap

from sddgrade.adapters.base import parse_sections
from sddgrade.catalog import load_catalog
from sddgrade.engine.lint import _plan_missing_distributed_tracing
from sddgrade.model import Artifact, ArtifactType

CATALOG = load_catalog()
PITFALL = "PLAN-MISSING-DISTRIBUTED-TRACING"


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
    return [f.pitfall_id for f in _plan_missing_distributed_tracing(art, CATALOG)]


# ---------------------------------------------------------------------------
# Firing cases — microservices vocab + deploy vocab, no tracing silence
# ---------------------------------------------------------------------------

def test_fires_microservices_no_tracing():
    """Plan describes microservices architecture with no distributed tracing."""
    art = _plan("""
        ## Deployment Plan
        Deploy the order management system to production this sprint.
        The system uses a microservices architecture with separate services
        for orders, inventory, and payments.
        Each service exposes a REST API consumed by the API gateway.
        Logs are forwarded to the central logging platform.
    """)
    assert _ids(art) == [PITFALL]


def test_fires_service_mesh_no_tracing():
    """Plan mentions service mesh with no distributed tracing strategy."""
    art = _plan("""
        ## Production Release
        Deploy the platform using a service mesh to manage inter-service
        communication and traffic routing.
        Monitoring uses Prometheus for metrics and Grafana for dashboards.
        No trace instrumentation is defined.
    """)
    assert _ids(art) == [PITFALL]


def test_fires_api_gateway_no_tracing():
    """Plan uses API gateway vocabulary with no distributed tracing."""
    art = _plan("""
        ## Release Plan
        The API gateway routes requests to backend services.
        Authentication is delegated to the identity service.
        Observability: centralized logging with Elasticsearch.
    """)
    assert _ids(art) == [PITFALL]


def test_fires_istio_no_otel():
    """Plan mentions Istio but no tracing backend configured."""
    art = _plan("""
        ## Infrastructure Plan
        Deploy the application using Istio for service discovery and
        traffic management in the Kubernetes cluster.
        Metrics exported via Prometheus; logging via Fluentd.
    """)
    assert _ids(art) == [PITFALL]


def test_fires_distributed_system_no_correlation():
    """Plan describes distributed system with no correlation ID strategy."""
    art = _plan("""
        ## Deployment Plan
        This sprint we deploy the distributed system consisting of
        the auth service, notification service, and billing service.
        Each service is containerised and deployed to EKS.
        Logging is centralised in CloudWatch.
    """)
    assert _ids(art) == [PITFALL]


def test_fires_multiple_services_no_tracing():
    """Plan explicitly calls out multiple services with no tracing."""
    art = _plan("""
        ## Deployment Checklist
        The release includes multiple services: user-service, email-service,
        and analytics-service. All services are deployed behind the load balancer.
        Each service has health checks and logging configured.
    """)
    assert _ids(art) == [PITFALL]


# ---------------------------------------------------------------------------
# Silent cases — tracing vocabulary present or no microservices trigger
# ---------------------------------------------------------------------------

def test_silent_otel_present():
    """Plan mentions OpenTelemetry — silenced."""
    art = _plan("""
        ## Deployment Plan
        The microservices architecture uses OpenTelemetry SDK for all services.
        Traces are exported via OTLP to Jaeger running in the ops namespace.
        W3C traceparent header is propagated across all HTTP calls.
    """)
    assert _ids(art) == []


def test_silent_jaeger_present():
    """Plan mentions Jaeger — silenced."""
    art = _plan("""
        ## Infrastructure
        Deploy multiple services to production.
        Distributed tracing is handled by Jaeger; sampling at 10%.
        All inter-service gRPC calls propagate trace headers.
    """)
    assert _ids(art) == []


def test_silent_correlation_id_present():
    """Plan mentions correlation_id — silenced."""
    art = _plan("""
        ## Deployment Plan
        The microservices communicate via a service mesh.
        Each request receives a correlation_id at the API gateway
        and propagated to downstream services via X-Correlation-ID header.
    """)
    assert _ids(art) == []


def test_silent_zipkin_present():
    """Plan mentions Zipkin — silenced."""
    art = _plan("""
        ## Release Notes
        Deploy the distributed system. Zipkin is configured for trace
        collection across all services. Head-based sampling at 5%.
    """)
    assert _ids(art) == []


def test_silent_monolith_no_microservices():
    """Monolithic deployment plan — no microservices trigger, check skips."""
    art = _plan("""
        ## Deployment Plan
        Deploy the monolithic Rails application to the production server.
        Run database migrations before starting the app process.
        Configure nginx as a reverse proxy in front of Puma.
        No distributed tracing needed for a single-process app.
    """)
    assert _ids(art) == []


def test_silent_no_deploy_vocab():
    """Plan without deployment vocabulary — deploy guard prevents false positives."""
    art = _plan("""
        ## Architecture Notes
        The system uses a microservices approach for scalability.
        Each service encapsulates a bounded domain context.
    """)
    assert _ids(art) == []


def test_silent_spec_artifact():
    """Spec artifact — check is plan-only, skips."""
    art = _spec("""
        ## Deployment Plan
        Deploy the microservices system to production this sprint.
        No distributed tracing strategy defined.
    """)
    assert _ids(art) == []


def test_silent_trace_id_header():
    """Plan mentions trace_id header — silenced."""
    art = _plan("""
        ## Deployment Plan
        Deploy the service mesh to production.
        All requests include a trace_id header injected at the ingress.
        Services forward trace_id to downstream calls.
    """)
    assert _ids(art) == []


def test_silent_linkerd_with_tracing():
    """Plan uses Linkerd with distributed tracing configured — silenced."""
    art = _plan("""
        ## Production Deployment
        The platform uses Linkerd as the service mesh.
        APM is provided by Datadog with distributed tracing enabled for
        all service-to-service calls.
    """)
    assert _ids(art) == []


def test_fires_envoy_no_tracing():
    """Plan mentions Envoy proxy with no tracing backend."""
    art = _plan("""
        ## Deployment Plan
        Deploy the platform using Envoy as the edge proxy and
        service-to-service communication layer.
        Metrics collected via Prometheus. No tracing backend defined.
    """)
    assert _ids(art) == [PITFALL]


def test_silent_fenced_microservice_keyword():
    """Microservices keyword inside a fenced code block is not a trigger."""
    art = _plan("""
        ## Deployment Plan
        Deploy the backend API to production.

        ```yaml
        # microservices config example
        services:
          - auth
          - payments
        ```

        The application is a monolith, the YAML is a reference example only.
    """)
    assert _ids(art) == []
