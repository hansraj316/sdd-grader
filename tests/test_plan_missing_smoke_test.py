"""Unit tests for PLAN-MISSING-SMOKE-TEST pitfall.

Fires when a deployment plan describes releasing to production/staging but has no
post-deploy smoke-test or verification strategy.

Sources: Kiro production-readiness gate, Tessl deploy checklist, Google SRE Book Ch.17.
"""
from __future__ import annotations

import textwrap

from sddgrade.adapters.base import parse_sections
from sddgrade.catalog import load_catalog
from sddgrade.engine.lint import _plan_missing_smoke_test
from sddgrade.model import Artifact, ArtifactType

CATALOG = load_catalog()
PITFALL = "PLAN-MISSING-SMOKE-TEST"


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


def _ids(findings):
    return [f.pitfall_id for f in findings]


# ---------------------------------------------------------------------------
# Fire cases
# ---------------------------------------------------------------------------


def test_fires_deploy_to_production_no_smoke():
    """Plan that deploys to production with no smoke test — should fire."""
    art = _plan("""
        # Deployment Plan

        ## Deployment

        Deploy the service to production using the standard release pipeline.
        Ensure the database migrations run first before enabling traffic.
    """)
    findings = _plan_missing_smoke_test(art, CATALOG)
    assert PITFALL in _ids(findings), f"Expected {PITFALL}, got {_ids(findings)}"


def test_fires_staging_environment_no_smoke():
    """Plan with staging environment deploy but no post-deploy verification — should fire."""
    art = _plan("""
        # Deployment Plan

        ## Deployment

        The service is deployed to the staging environment via CI/CD.
        Feature flags are toggled after the staging deploy completes.
    """)
    findings = _plan_missing_smoke_test(art, CATALOG)
    assert PITFALL in _ids(findings), f"Expected {PITFALL}, got {_ids(findings)}"


def test_fires_go_live_no_smoke():
    """Plan that mentions go-live with no smoke test — should fire."""
    art = _plan("""
        # Deployment Plan

        ## Deployment

        The app is deployed via Kubernetes.

        ## Go-Live Checklist

        On go-live day, the ops team triggers the production release pipeline.
        Run the database migration script before enabling traffic.
    """)
    findings = _plan_missing_smoke_test(art, CATALOG)
    assert PITFALL in _ids(findings), f"Expected {PITFALL}, got {_ids(findings)}"


def test_fires_production_environment_no_smoke():
    """Plan mentioning production environment with no verification — should fire."""
    art = _plan("""
        # Deployment Plan

        ## Deployment

        The application is deployed to AWS EKS.

        ## Infrastructure

        The service runs in the production environment on AWS EKS.
        Horizontal pod autoscaling is configured with min=2, max=10 replicas.
    """)
    findings = _plan_missing_smoke_test(art, CATALOG)
    assert PITFALL in _ids(findings), f"Expected {PITFALL}, got {_ids(findings)}"


def test_fires_release_to_prod_no_smoke():
    """Plan with 'release to production' language but no smoke test — should fire."""
    art = _plan("""
        # Deployment Plan

        ## Deployment

        Deploy the application.

        ## Release

        On merge to main, the CI/CD pipeline triggers a release to production.
        The artifact is tagged with the git SHA and pushed to ECR.
    """)
    findings = _plan_missing_smoke_test(art, CATALOG)
    assert PITFALL in _ids(findings), f"Expected {PITFALL}, got {_ids(findings)}"


# ---------------------------------------------------------------------------
# Silent cases
# ---------------------------------------------------------------------------


def test_silent_smoke_test_present():
    """Plan with smoke tests explicitly mentioned — should NOT fire."""
    art = _plan("""
        # Deployment Plan

        ## Deployment

        Deploy to production using the standard release pipeline.

        ## Post-Deploy Verification

        After deploy, run the smoke test suite against the production endpoint.
        If any smoke test fails, trigger the rollback runbook.
    """)
    findings = _plan_missing_smoke_test(art, CATALOG)
    assert PITFALL not in _ids(findings), f"Should be silent, got {_ids(findings)}"


def test_silent_post_deploy_verification():
    """Plan with post-deploy validation — should NOT fire."""
    art = _plan("""
        # Deployment Plan

        ## Deployment

        The service is deployed via ArgoCD.
        Release to production on every merge to main.
        Post-deploy verification: the /health endpoint must return 200 within 30 s.
    """)
    findings = _plan_missing_smoke_test(art, CATALOG)
    assert PITFALL not in _ids(findings), f"Should be silent, got {_ids(findings)}"


def test_silent_sanity_check_mentioned():
    """Plan with sanity check after deployment — should NOT fire."""
    art = _plan("""
        # Deployment Plan

        ## Deployment

        Deploy the application using the GitOps pipeline.
        Promote the image to the production environment.
        Perform a sanity check by hitting the /health and /metrics endpoints.
    """)
    findings = _plan_missing_smoke_test(art, CATALOG)
    assert PITFALL not in _ids(findings), f"Should be silent, got {_ids(findings)}"


def test_silent_no_production_vocab():
    """Plan with no production/staging vocabulary at all — should NOT fire."""
    art = _plan("""
        # Deployment Plan

        ## Deployment

        The service is deployed via Docker Compose on the developer's machine.

        ## Architecture

        The service uses a microservices architecture with REST APIs.
        Data is stored in PostgreSQL and cached in Redis.
    """)
    findings = _plan_missing_smoke_test(art, CATALOG)
    assert PITFALL not in _ids(findings), f"Should be silent, got {_ids(findings)}"


def test_silent_not_a_plan_artifact():
    """Spec artifact — should NOT fire."""
    art = _spec("""
        # Functional Specification

        ## Requirements

        FR-001: The system shall allow users to log in.
        FR-002: The system shall send email notifications.
        Production environment configuration is TBD.
    """)
    findings = _plan_missing_smoke_test(art, CATALOG)
    assert PITFALL not in _ids(findings), f"Should be silent, got {_ids(findings)}"


def test_silent_deploy_validation_mentioned():
    """Plan with deployment validation — should NOT fire."""
    art = _plan("""
        # Deployment Plan

        ## Deployment

        Deploy to production via ArgoCD.

        ## Validation

        Deployment validation: run the end-to-end acceptance test suite after deploy.
        If tests fail, the deployment is automatically rolled back.
    """)
    findings = _plan_missing_smoke_test(art, CATALOG)
    assert PITFALL not in _ids(findings), f"Should be silent, got {_ids(findings)}"


def test_silent_fenced_prod_only():
    """Plan where production mention is inside a fenced code block — should NOT fire."""
    art = _plan("""
        # Deployment Plan

        ## Deployment

        Deploy the application using the following command:

        ```bash
        kubectl apply -f production-environment/
        ```

        No other configuration required.
    """)
    findings = _plan_missing_smoke_test(art, CATALOG)
    assert PITFALL not in _ids(findings), f"Should be silent, got {_ids(findings)}"


def test_fires_line_number_is_reasonable():
    """Finding is anchored at a line with the production deploy vocabulary."""
    raw = textwrap.dedent("""
        # Deployment Plan

        ## Deployment

        The service is containerized and deployed to production via Kubernetes.
        No post-deploy checks are defined.
    """).strip()
    art = Artifact(
        path="plan.md",
        type=ArtifactType.PLAN,
        feature_id="test",
        raw=raw,
        sections=parse_sections(raw),
    )
    findings = _plan_missing_smoke_test(art, CATALOG)
    assert findings, "Expected at least one finding"
    total_lines = len(raw.splitlines())
    assert 1 < findings[0].line <= total_lines, (
        f"Finding line {findings[0].line} is outside expected range"
    )
