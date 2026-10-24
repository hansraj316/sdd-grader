"""Tests for PLAN-NO-MULTI-REPLICA pitfall.

Fires when a plan.md with deployment vocabulary AND container/K8s vocabulary
has no replica count or high-availability strategy specified.

Sources: CNCF Production Readiness Checklist (multiple instances required);
         AWS Well-Architected Framework REL-10 (multiple AZ/instance deployment);
         Google SRE Book Chapter 26 (≥2 replicas for user-facing services);
         Kiro HA gate (replica count required before ship).
"""
from __future__ import annotations

import textwrap

from sddgrade.adapters.base import parse_sections
from sddgrade.catalog import load_catalog
from sddgrade.engine.lint import _plan_no_multi_replica
from sddgrade.model import Artifact, ArtifactType

CATALOG = load_catalog()
PITFALL = "PLAN-NO-MULTI-REPLICA"


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
    return [f.pitfall_id for f in _plan_no_multi_replica(art, CATALOG)]


# ---------------------------------------------------------------------------
# Firing cases — K8s/container vocab present, no replica/HA vocabulary
# ---------------------------------------------------------------------------


def test_fires_kubernetes_no_replicas():
    """Plan deploys to Kubernetes but has no replica count."""
    art = _plan("""
        ## Deployment Plan
        Deploy the web service to the production Kubernetes cluster.
        The service runs as a pod in the default namespace.
        Rolling updates will be used for zero-downtime deploys.
    """)
    assert PITFALL in _ids(art)


def test_fires_helm_chart_no_ha():
    """Plan references a Helm chart with no HA or replica mention."""
    art = _plan("""
        ## Deployment Plan
        Install the application using the Helm chart from the internal registry.
        `helm upgrade --install myapp ./charts/myapp`
        No values override for availability or scaling.
    """)
    assert PITFALL in _ids(art)


def test_fires_k8s_abbreviation_no_replicas():
    """Plan uses k8s abbreviation but no replica spec."""
    art = _plan("""
        ## Release Plan
        Push to k8s via the CI pipeline.
        Apply the deployment manifest with kubectl.
    """)
    assert PITFALL in _ids(art)


def test_fires_pod_vocab_no_ha():
    """Plan mentions pod but no HA or replica count."""
    art = _plan("""
        ## Deployment Plan
        The scheduler creates a new pod for each job instance.
        No scaling or availability policy is defined.
    """)
    assert PITFALL in _ids(art)


def test_fires_deployment_yaml_no_replicas():
    """Plan references deployment.yaml but no replica section."""
    art = _plan("""
        ## Release Plan
        Apply the deployment.yaml manifest to the production cluster.
        Rollout strategy: RollingUpdate with maxSurge=1.
    """)
    assert PITFALL in _ids(art)


# ---------------------------------------------------------------------------
# Silent cases — replica/HA vocabulary present or no K8s trigger
# ---------------------------------------------------------------------------


def test_silent_replicas_keyword():
    """Plan has 'replicas: 3' — should not fire."""
    art = _plan("""
        ## Deployment Plan
        Deploy the service to Kubernetes with replicas: 3.
        Rolling updates will replace pods one at a time.
    """)
    assert PITFALL not in _ids(art)


def test_silent_hpa_mentioned():
    """Plan mentions HPA — should not fire."""
    art = _plan("""
        ## Deployment Plan
        Deploy to Kubernetes with an HPA targeting 70% CPU utilisation.
        Scale from 2 to 10 pods based on load.
    """)
    assert PITFALL not in _ids(art)


def test_silent_high_availability_mentioned():
    """Plan mentions high-availability strategy — should not fire."""
    art = _plan("""
        ## Deployment Plan
        Deploy the service using the Helm chart.
        The service is configured for high-availability across three AZs.
    """)
    assert PITFALL not in _ids(art)


def test_silent_autoscaling_mentioned():
    """Plan mentions autoscaling — should not fire."""
    art = _plan("""
        ## Deployment Plan
        The Kubernetes deployment uses horizontal pod autoscaler (auto-scaling
        from 2 to 20 instances based on CPU load).
    """)
    assert PITFALL not in _ids(art)


def test_silent_no_k8s_vocab():
    """Plan has no container/K8s vocabulary — check does not fire."""
    art = _plan("""
        ## Deployment Plan
        Deploy the application as a systemd service on the bare-metal server.
        No rollback strategy needed for this release.
    """)
    assert PITFALL not in _ids(art)


def test_silent_k8s_vocab_in_fenced_block():
    """K8s vocab only inside a fenced code block — should not fire."""
    art = _plan("""
        ## Deployment Plan
        The following is an example manifest:
        ```yaml
        apiVersion: apps/v1
        kind: Deployment
        spec:
          selector:
            matchLabels:
              app: web
        ```
        No container-based deployment planned.
    """)
    assert PITFALL not in _ids(art)


def test_silent_asg_mentioned():
    """Plan mentions ASG (Auto Scaling Group) — should not fire."""
    art = _plan("""
        ## Deployment Plan
        Deploy the Docker Compose stack on EC2 instances managed by an ASG.
        Minimum 2 instances are maintained.
    """)
    assert PITFALL not in _ids(art)


def test_silent_multi_instance_mentioned():
    """Plan mentions multi-instance — should not fire."""
    art = _plan("""
        ## Deployment Plan
        Deploy as a multi-instance kubernetes cluster for high throughput.
        Each pod handles a segment of the traffic.
    """)
    assert PITFALL not in _ids(art)


def test_does_not_fire_on_spec():
    """Spec artifact — check is plan-only, must not fire."""
    art = _spec("""
        ## Requirements
        FR-1 The system shall deploy using Kubernetes pods.
        FR-2 The system shall have multiple replicas for availability.
    """)
    assert PITFALL not in _ids(art)
