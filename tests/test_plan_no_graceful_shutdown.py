"""Tests for PLAN-NO-GRACEFUL-SHUTDOWN pitfall.

Fires when a plan.md with deployment vocabulary AND process stop/restart
vocabulary has no graceful-shutdown strategy (graceful/drain/in-flight/
pre-stop/lifecycle hook/terminationGracePeriodSeconds/stop timeout/etc.)
anywhere in the document.

Sources: Twelve-Factor App Factor VI (Disposability);
         Amazon Kiro production-readiness checklist;
         ISO/IEC 25010:2011 §4.2.1.4 Fault Tolerance.
"""
from __future__ import annotations

import textwrap

from sddgrade.adapters.base import parse_sections
from sddgrade.catalog import load_catalog
from sddgrade.engine.lint import _plan_no_graceful_shutdown
from sddgrade.model import Artifact, ArtifactType

CATALOG = load_catalog()
PITFALL = "PLAN-NO-GRACEFUL-SHUTDOWN"


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
    return [f.pitfall_id for f in _plan_no_graceful_shutdown(art, CATALOG)]


# ---------------------------------------------------------------------------
# Firing cases — stop/restart vocab present, no graceful-shutdown token
# ---------------------------------------------------------------------------


def test_fires_restart_no_graceful():
    """Plan mentions restart with no graceful-shutdown strategy."""
    art = _plan("""
        ## Deployment Plan
        We will deploy the API service to production.
        The deployment will restart all running pods during the upgrade.
        No shutdown strategy is documented in this plan.
    """)
    assert PITFALL in _ids(art)


def test_fires_rolling_update_no_drain():
    """Plan describes a rolling update with no connection drain strategy."""
    art = _plan("""
        ## Release Plan
        Deploy version 2.1.0 to production via Kubernetes.
        We will use a rolling update to replace old pods with new ones.
        Requests in progress at switchover time will be handled by the new version.
    """)
    assert PITFALL in _ids(art)


def test_fires_zero_downtime_no_shutdown_hook():
    """Plan claims zero-downtime deploy but no lifecycle hook is mentioned."""
    art = _plan("""
        ## Production Deployment
        This release targets zero-downtime deployment via blue-green switch.
        The load balancer will redirect traffic when health checks pass.
        Process termination sequence is not documented here.
    """)
    assert PITFALL in _ids(art)


def test_fires_sigterm_no_handler():
    """Plan sends SIGTERM to processes but documents no signal handler."""
    art = _plan("""
        ## Deployment Plan
        Deploy the worker service to the production cluster.
        During updates the orchestrator sends SIGTERM to old processes.
        Worker behavior on receiving the signal is not specified.
    """)
    assert PITFALL in _ids(art)


def test_fires_shutdown_no_strategy():
    """Plan mentions 'shutdown' with no graceful strategy."""
    art = _plan("""
        ## Deployment
        Release the new version of the payment service.
        During shutdown the process is immediately replaced by the new container.
        No request handling strategy is described for the transition period.
    """)
    assert PITFALL in _ids(art)


def test_fires_stop_no_graceful():
    """Plan says the deploy script stops old instances but no shutdown strategy."""
    art = _plan("""
        ## Release Plan
        Deploy the notification service to production.
        The deploy script stops old instances before bringing up the new ones.
        Database connections are closed immediately with no shutdown strategy described.
    """)
    assert PITFALL in _ids(art)


def test_fires_canary_deploy_no_lifecycle():
    """Plan uses canary deployment but no lifecycle hook or drain is mentioned."""
    art = _plan("""
        ## Deployment Plan
        We will use a canary deploy to gradually shift traffic to the new version.
        Old instances are terminated once traffic reaches 100% on the canary.
        No process lifecycle strategy is documented for the termination sequence.
    """)
    assert PITFALL in _ids(art)


# ---------------------------------------------------------------------------
# Silent cases — graceful-shutdown / drain / in-flight vocabulary present
# ---------------------------------------------------------------------------


def test_silent_graceful_keyword():
    """Plan explicitly mentions graceful shutdown — silenced."""
    art = _plan("""
        ## Deployment Plan
        Deploy the API service to production via rolling update.
        On SIGTERM the server stops accepting new requests and gracefully
        finishes in-flight requests before exiting.
        terminationGracePeriodSeconds is set to 30.
    """)
    assert PITFALL not in _ids(art)


def test_silent_connection_drain():
    """Plan describes connection draining — silenced."""
    art = _plan("""
        ## Release Plan
        Perform a rolling update on the Kubernetes cluster.
        Before restarting old pods, the load balancer performs connection drain
        to allow active requests to complete.
    """)
    assert PITFALL not in _ids(art)


def test_silent_in_flight_mentioned():
    """Plan addresses in-flight requests explicitly — silenced."""
    art = _plan("""
        ## Production Deployment
        The rolling update strategy ensures zero-downtime deployment.
        All in-flight requests are allowed to complete before the old container stops.
        New containers start accepting traffic only after passing readiness checks.
    """)
    assert PITFALL not in _ids(art)


def test_silent_pre_stop_hook():
    """Plan defines a pre-stop lifecycle hook — silenced."""
    art = _plan("""
        ## Deployment
        Deploy the web service to production using Kubernetes rolling update.
        A pre-stop hook calls /healthz/shutdown and waits for active connections to close.
        The terminationGracePeriodSeconds is 60.
    """)
    assert PITFALL not in _ids(art)


def test_silent_draining():
    """Plan uses 'draining' — silenced."""
    art = _plan("""
        ## Release Plan
        The old instances are kept in a draining state while active connections complete.
        Once all connections close, the instance is terminated.
        Restart of the service will only proceed after the drain window expires.
    """)
    assert PITFALL not in _ids(art)


def test_silent_lifecycle_hook():
    """Plan mentions a lifecycle hook — silenced."""
    art = _plan("""
        ## Production Deployment
        Zero-downtime rolling deploy is used to update the API.
        A lifecycle hook delays termination until the ELB deregisters the instance.
        This ensures no in-progress requests are dropped on restart.
    """)
    assert PITFALL not in _ids(art)


def test_silent_termination_grace_period():
    """Plan sets terminationGracePeriodSeconds — silenced."""
    art = _plan("""
        ## Deployment Plan
        Kubernetes rolling update replaces pods one at a time.
        terminationGracePeriodSeconds: 30 ensures SIGTERM handling before SIGKILL.
        Workers return jobs to the queue before exiting.
    """)
    assert PITFALL not in _ids(art)


def test_silent_no_process_stop_vocab():
    """Plan has deployment vocab but no process stop/restart vocabulary — not applicable."""
    art = _plan("""
        ## Deployment Plan
        Deploy the frontend bundle to the CDN.
        All files are static and served from an edge cache.
        No process lifecycle changes are required.
    """)
    assert PITFALL not in _ids(art)


def test_silent_no_deploy_vocab():
    """No deployment section or vocab — deploy guard prevents false positive."""
    art = _plan("""
        ## Engineering Notes
        Consider how to handle process shutdown in the worker library.
        This document covers general design patterns only.
    """)
    assert PITFALL not in _ids(art)


def test_silent_spec_artifact():
    """Check does not apply to spec artifacts — skipped."""
    art = _spec("""
        ## Deployment Plan
        Deploy the service to production.
        The system shall restart all workers on failure.
        No graceful shutdown strategy is defined.
    """)
    assert PITFALL not in _ids(art)


def test_silent_fenced_stop_only():
    """Process stop vocabulary only inside a fenced code block — not a trigger."""
    art = _plan("""
        ## Deployment Plan
        Deploy the API to production.

        ```bash
        systemctl stop myservice
        systemctl restart myservice
        ```

        The service uses a graceful drain window for in-flight requests;
        the code block above is illustrative only.
    """)
    assert PITFALL not in _ids(art)


def test_fires_once_aggregate():
    """Multiple restart references fire only one finding."""
    art = _plan("""
        ## Deployment Plan
        Deploy the service to production via rolling update.
        Step 1: restart the API pods.
        Step 2: restart the worker pods.
        Step 3: verify health checks pass.
    """)
    findings = _plan_no_graceful_shutdown(art, CATALOG)
    assert len([f for f in findings if f.pitfall_id == PITFALL]) == 1
