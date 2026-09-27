"""Tests for PLAN-CONTAINER-NO-RESOURCE-LIMITS pitfall.

Fires when a plan.md with deployment vocabulary AND container/orchestration
vocabulary has no resource limits or requests specified.

Sources: Kiro production-readiness gate (resource limits required before ship);
         Tessl container resource governance;
         CNCF production checklist (resources.limits + resources.requests);
         ISO 25010 Capacity (system shall not exceed allocated resource envelope).
"""
from __future__ import annotations

import textwrap

from sddgrade.adapters.base import parse_sections
from sddgrade.catalog import load_catalog
from sddgrade.engine.lint import _plan_container_no_resource_limits
from sddgrade.model import Artifact, ArtifactType

CATALOG = load_catalog()
PITFALL = "PLAN-CONTAINER-NO-RESOURCE-LIMITS"


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
    return [f.pitfall_id for f in _plan_container_no_resource_limits(art, CATALOG)]


# ---------------------------------------------------------------------------
# Firing cases — container vocab present, no resource limits
# ---------------------------------------------------------------------------


def test_fires_kubernetes_no_limits():
    """Plan deploys to Kubernetes but has no resource limits."""
    art = _plan("""
        ## Deployment Plan
        Deploy the web service to the production Kubernetes cluster.
        The service runs as a pod in the default namespace.
        Rolling updates will be used for zero-downtime deploys.
    """)
    assert PITFALL in _ids(art)


def test_fires_docker_no_limits():
    """Plan uses Docker but specifies no mem_limit or cpu_shares."""
    art = _plan("""
        ## Release Plan
        Deploy using Docker containers on the EC2 instance.
        Run `docker run -d payment-service:latest`.
        No resource constraints are configured.
    """)
    assert PITFALL in _ids(art)


def test_fires_helm_chart_no_resources():
    """Plan references a Helm chart with no resource values."""
    art = _plan("""
        ## Deployment Plan
        Install the application using the Helm chart from the internal registry.
        `helm upgrade --install myapp ./charts/myapp`
        No values override for resource quotas.
    """)
    assert PITFALL in _ids(art)


def test_fires_k8s_abbreviation_no_limits():
    """Plan uses k8s abbreviation but no resource spec."""
    art = _plan("""
        ## Release Plan
        Push to k8s via the CI pipeline.
        Apply the deployment manifest with kubectl.
    """)
    assert PITFALL in _ids(art)


def test_fires_pod_vocab_no_limits():
    """Plan mentions pod but no resource limits."""
    art = _plan("""
        ## Deployment Plan
        The scheduler creates a new pod for each job instance.
        No CPU or memory constraints are defined.
    """)
    assert PITFALL in _ids(art)


def test_fires_deployment_yaml_no_limits():
    """Plan references deployment.yaml but no resource section."""
    art = _plan("""
        ## Release Plan
        Apply the deployment.yaml manifest to the production cluster.
        Rollout strategy: RollingUpdate with maxSurge=1.
    """)
    assert PITFALL in _ids(art)


# ---------------------------------------------------------------------------
# Silent cases — resource limits are present
# ---------------------------------------------------------------------------


def test_silent_resources_limits_key():
    """Plan has resources.limits — should not fire."""
    art = _plan("""
        ## Deployment Plan
        Deploy the service to Kubernetes.
        Each pod has resources.limits of cpu: 500m, memory: 512Mi.
    """)
    assert PITFALL not in _ids(art)


def test_silent_resources_requests_key():
    """Plan specifies resources.requests — silent."""
    art = _plan("""
        ## Deployment Plan
        Deploy the Docker container via Kubernetes.
        resources.requests: cpu: 100m, memory: 128Mi.
    """)
    assert PITFALL not in _ids(art)


def test_silent_limits_colon_yaml():
    """Plan includes a 'limits:' YAML key — silent."""
    art = _plan("""
        ## Deployment Plan
        Apply the k8s manifest:
        resources:
          limits:
            cpu: "1"
            memory: "1Gi"
    """)
    assert PITFALL not in _ids(art)


def test_silent_cpu_limit_prose():
    """Plan states 'cpu limit' in prose — silent."""
    art = _plan("""
        ## Release Plan
        The Kubernetes pod has a cpu limit of 500m and memory limit of 256Mi.
    """)
    assert PITFALL not in _ids(art)


def test_silent_mem_limit_compose():
    """Plan uses Docker Compose mem_limit — silent."""
    art = _plan("""
        ## Deployment Plan
        Deploy using Docker containers.
        Set mem_limit: 512m in docker-compose.yml.
    """)
    assert PITFALL not in _ids(art)


def test_silent_no_container_vocab():
    """Plan has no container vocabulary — check does not fire."""
    art = _plan("""
        ## Deployment Plan
        Deploy the application as a systemd service on the bare-metal server.
        No rollback strategy needed for this release.
    """)
    assert PITFALL not in _ids(art)


def test_silent_requests_colon_yaml():
    """Plan includes a 'requests:' YAML key — silent."""
    art = _plan("""
        ## Deployment Plan
        Apply the k8s manifest to the cluster:
        resources:
          requests:
            cpu: "250m"
            memory: "256Mi"
        The pod runs the web service.
    """)
    assert PITFALL not in _ids(art)


def test_silent_container_in_fenced_block():
    """Container vocab only inside a fenced code block — should not fire."""
    art = _plan("""
        ## Deployment Plan
        The following is an example manifest:
        ```yaml
        kind: Deployment
        spec:
          containers:
            - name: app
              image: my-docker-image:latest
        ```
        No resource limits needed per our policy.
    """)
    assert PITFALL not in _ids(art)


def test_does_not_fire_on_spec():
    """Spec artifact — check is plan-only, must not fire."""
    art = _spec("""
        ## Requirements
        FR-1 The system shall deploy using Kubernetes pods.
        FR-2 The system shall have no resource limit violations.
    """)
    assert PITFALL not in _ids(art)
