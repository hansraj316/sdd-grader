"""Tests for PLAN-NO-STRUCTURED-LOGGING pitfall check.

Fires when a deployment plan mentions application logging but names no
structured log format (JSON logs, logfmt, ECS) or log schema strategy.

Sources: 12-Factor App Principle XI (https://12factor.net/logs);
OpenTelemetry Logging spec; Kiro production-readiness observability gate;
Tessl engineering standards.
"""
from __future__ import annotations

import textwrap

from sddgrade.adapters.base import parse_sections
from sddgrade.catalog import load_catalog
from sddgrade.engine.lint import _plan_no_structured_logging
from sddgrade.model import Artifact, ArtifactType

CATALOG = load_catalog()
PITFALL = "PLAN-NO-STRUCTURED-LOGGING"


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
    return [f.pitfall_id for f in _plan_no_structured_logging(art, CATALOG)]


# ---------------------------------------------------------------------------
# FIRE cases
# ---------------------------------------------------------------------------

def test_fires_application_log_no_format():
    """Plan mentions application log but no structured format → fires."""
    art = _plan("""
        # Deployment Plan

        ## Deploy

        The service writes application log output to stdout.
        Logs are shipped to CloudWatch for storage and retention.
    """)
    assert PITFALL in _ids(art)


def test_fires_logger_no_format():
    """Plan mentions a logger with no log format specified → fires."""
    art = _plan("""
        # Deployment Plan

        ## Deploy

        A centralized logger writes error log entries to the ELK stack.
        The team will decide on aggregation later.
    """)
    assert PITFALL in _ids(art)


def test_fires_access_log_no_format():
    """Plan has access log but no structured format → fires."""
    art = _plan("""
        # Deployment Plan

        ## Deploy

        Nginx generates access log output for each HTTP request.
        Logs are retained for 30 days in S3.
    """)
    assert PITFALL in _ids(art)


def test_fires_service_log_no_format():
    """Plan has service log but no format strategy → fires."""
    art = _plan("""
        # Deployment Plan

        ## Deploy

        Each service log is collected via a sidecar container.
        No schema or format is documented.
    """)
    assert PITFALL in _ids(art)


def test_fires_logs_all_requests_no_format():
    """Plan logs all requests with no structured format → fires."""
    art = _plan("""
        # Deployment Plan

        ## Deploy

        The API gateway logs all requests and responses to CloudWatch.
        Retention is set to 90 days.
    """)
    assert PITFALL in _ids(art)


def test_fires_audit_log_no_format():
    """Plan has audit log with no structured format → fires."""
    art = _plan("""
        # Deployment Plan

        ## Deploy

        Privileged admin actions are recorded in an audit log
        stored in a separate S3 bucket.
    """)
    assert PITFALL in _ids(art)


# ---------------------------------------------------------------------------
# SILENT cases
# ---------------------------------------------------------------------------

def test_silent_json_structured_logging():
    """Plan specifies JSON structured logging → no finding."""
    art = _plan("""
        # Deployment Plan

        ## Deploy

        All services emit structured JSON logs to stdout.
        Fields: timestamp, level, service, trace_id, message.
        Fluentd DaemonSet ships logs to Datadog.
    """)
    assert PITFALL not in _ids(art)


def test_silent_structured_logging_keyword():
    """Plan uses 'structured logging' keyword → no finding."""
    art = _plan("""
        # Deployment Plan

        ## Deploy

        The application logger writes application log events using
        structured logging. Logs are forwarded to Loki.
    """)
    assert PITFALL not in _ids(art)


def test_silent_logfmt():
    """Plan specifies logfmt format → no finding."""
    art = _plan("""
        # Deployment Plan

        ## Deploy

        Services write application log output in logfmt format for
        easy parsing and querying.
    """)
    assert PITFALL not in _ids(art)


def test_silent_otel_logs():
    """Plan uses OpenTelemetry log format → no finding."""
    art = _plan("""
        # Deployment Plan

        ## Deploy

        Application log events are emitted via the OpenTelemetry log
        exporter in otel log format.
    """)
    assert PITFALL not in _ids(art)


def test_silent_no_logging_vocab():
    """Plan has no logging vocabulary → no finding."""
    art = _plan("""
        # Deployment Plan

        ## Deploy

        The service is deployed to Kubernetes with autoscaling.
        Health checks are configured on /healthz.
    """)
    assert PITFALL not in _ids(art)


def test_silent_non_plan_artifact():
    """Non-plan artifact (spec) → no finding."""
    art = _spec("""
        # Spec

        ## Requirements

        FR-001: The system shall support user authentication.
        The service logs all requests to the audit log.
    """)
    assert PITFALL not in _ids(art)


def test_silent_no_deploy_vocab():
    """Plan with logging vocab but no deploy section/vocab → no finding."""
    art = _plan("""
        # Notes

        The logger writes application log entries to a file.
        This is an internal reference document.
    """)
    assert PITFALL not in _ids(art)


def test_silent_trigger_in_fenced_block():
    """Logging trigger only inside fenced code block → no finding."""
    art = _plan("""
        # Deployment Plan

        ## Deploy

        Configure the following YAML settings:

        ```yaml
        logger:
          output: application log
          level: info
        ```

        Adjust as needed for the environment.
    """)
    assert PITFALL not in _ids(art)


def test_silent_trigger_on_heading_line():
    """Logging vocab only in a heading line → no finding."""
    art = _plan("""
        # Deployment Plan

        ## Deploy

        Deploy the application to production.

        ## Application Log

        No logging format is documented here.
    """)
    assert PITFALL not in _ids(art)


def test_silent_ecs_format():
    """Plan uses ECS format → no finding."""
    art = _plan("""
        # Deployment Plan

        ## Deploy

        All service log output is formatted using the ECS format
        for compatibility with Elastic Stack.
    """)
    assert PITFALL not in _ids(art)
