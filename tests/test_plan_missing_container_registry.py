"""Tests for PLAN-MISSING-CONTAINER-REGISTRY pitfall check.

Fires when a plan.md with deployment vocabulary AND container/Docker/Kubernetes
vocabulary has no container image registry strategy anywhere in the non-fenced text.

Source: Kiro production-readiness; Tessl Deployment Checklist; CNCF best practices;
OWASP CICD-SEC-9 (use of untrusted artifacts).
"""
from __future__ import annotations

import textwrap

from sddgrade.adapters.base import parse_sections
from sddgrade.catalog import load_catalog
from sddgrade.engine.lint import _plan_missing_container_registry
from sddgrade.model import Artifact, ArtifactType

CATALOG = load_catalog()
PITFALL = "PLAN-MISSING-CONTAINER-REGISTRY"


def _plan(raw: str) -> Artifact:
    raw = textwrap.dedent(raw).strip()
    return Artifact(
        path="plan.md",
        type=ArtifactType.PLAN,
        feature_id="test",
        raw=raw,
        sections=parse_sections(raw),
    )


def _fires(raw: str) -> bool:
    findings = _plan_missing_container_registry(_plan(raw), CATALOG)
    return any(f.pitfall_id == PITFALL for f in findings)


# ---------------------------------------------------------------------------
# Fire cases (≥5)
# ---------------------------------------------------------------------------

def test_docker_plan_no_registry():
    """Docker deployment plan with no registry should fire."""
    assert _fires(
        """\
        ## Deployment Plan

        We deploy the application using Docker on an EC2 instance.
        The docker image is built in CI and deployed to the server.
        """
    )


def test_kubernetes_plan_no_registry():
    """Kubernetes plan with no registry strategy should fire."""
    assert _fires(
        """\
        ## Release Plan

        Deploy to production Kubernetes cluster.
        The pod spec references the application container image.
        No persistent storage is required.
        """
    )


def test_helm_chart_no_registry():
    """Helm chart deployment without registry strategy should fire."""
    assert _fires(
        """\
        ## Deployment

        We use a helm chart to deploy the service to the staging cluster.
        The chart values are stored in the config repo.
        """
    )


def test_oci_image_no_registry():
    """OCI image deployment without registry strategy should fire."""
    assert _fires(
        """\
        ## Production Deploy

        The service is packaged as an OCI image and run on the host.
        Images are pushed from the CI pipeline to the deployment server.
        """
    )


def test_k8s_abbreviation_no_registry():
    """k8s abbreviation triggers without registry strategy."""
    assert _fires(
        """\
        ## Deployment

        Deploy to k8s using a standard deployment manifest.
        Rolling updates are configured in the manifest.
        """
    )


# ---------------------------------------------------------------------------
# Silent cases (≥8)
# ---------------------------------------------------------------------------

def test_ecr_silences():
    """ECR mention silences the check."""
    assert not _fires(
        """\
        ## Deployment

        We deploy using Docker on Kubernetes.
        Images are stored in Amazon ECR with semver tagging.
        The image pull policy is set to IfNotPresent.
        """
    )


def test_gcr_silences():
    """GCR mention silences the check."""
    assert not _fires(
        """\
        ## Release Plan

        Deploy the container image to production Kubernetes.
        Images are pushed to GCR (gcr.io/myproject/myapp) during CI.
        """
    )


def test_ghcr_silences():
    """ghcr.io mention silences the check."""
    assert not _fires(
        """\
        ## Deployment

        Build and deploy the Docker image using GitHub Actions.
        Images are published to ghcr.io/org/repo with SHA-based tags.
        """
    )


def test_docker_hub_silences():
    """Docker Hub mention silences the check."""
    assert not _fires(
        """\
        ## Deployment Plan

        The application runs in a Docker container on a VM.
        Images are pulled from docker hub with a specific pinned version.
        """
    )


def test_registry_keyword_silences():
    """Generic 'registry' keyword silences the check."""
    assert not _fires(
        """\
        ## Production Deploy

        All container images are stored in the internal container registry.
        The registry is scanned with Trivy before each deployment.
        """
    )


def test_harbor_silences():
    """Harbor registry mention silences the check."""
    assert not _fires(
        """\
        ## Deployment

        Deploy the Docker image to Kubernetes.
        Images are stored in Harbor with Clair vulnerability scanning enabled.
        Image tags follow semver: 1.2.3.
        """
    )


def test_no_container_vocab_no_fire():
    """Plan without container vocabulary should not fire even without registry."""
    assert not _fires(
        """\
        ## Deployment Plan

        Deploy the application to an EC2 instance running Ubuntu.
        The application is started via systemd.
        """
    )


def test_container_in_fenced_block_no_fire():
    """Container vocab inside fenced block should not trigger."""
    assert not _fires(
        """\
        ## Deployment Plan

        We deploy to production via the CI pipeline.

        ```yaml
        docker build -t myapp:latest .
        docker push myapp:latest
        ```

        The service is managed by systemd.
        """
    )


def test_non_plan_artifact_no_fire():
    """Check only applies to plan artifacts, not specs."""
    raw = textwrap.dedent(
        """\
        ## Spec

        Deploy the Docker image to Kubernetes with no registry mention.
        """
    ).strip()
    spec_art = Artifact(
        path="spec.md",
        type=ArtifactType.SPEC,
        feature_id="test",
        raw=raw,
        sections=parse_sections(raw),
    )
    findings = _plan_missing_container_registry(spec_art, CATALOG)
    assert not any(f.pitfall_id == PITFALL for f in findings)


def test_image_tag_silences():
    """Image tag strategy mention silences the check."""
    assert not _fires(
        """\
        ## Deployment Plan

        Build the Docker container image and deploy to Kubernetes.
        Each image tag follows semver (e.g. 1.2.3) for production releases.
        """
    )
