"""Tests for PLAN-NO-MULTI-TENANT-ISOLATION pitfall.

Fires when a deployment plan references multi-tenant/SaaS vocabulary
(multi-tenant, tenant_id, per-tenant, SaaS platform, …) but contains
no tenant data isolation strategy (row-level security, schema-per-tenant,
database-per-tenant, tenant isolation, …).

Sources: AWS Well-Architected SaaS Lens; OWASP Multi-Tenancy Cheat Sheet;
PostgreSQL Row Security Policies; ISO 27001 A.9.4; Kiro production-readiness.
"""
from __future__ import annotations

import textwrap

from sddgrade.adapters.base import parse_sections
from sddgrade.catalog import load_catalog
from sddgrade.engine.lint import _plan_no_multi_tenant_isolation
from sddgrade.model import Artifact, ArtifactType

CATALOG = load_catalog()
PITFALL = "PLAN-NO-MULTI-TENANT-ISOLATION"


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
    return [f.pitfall_id for f in _plan_no_multi_tenant_isolation(art, CATALOG)]


# ---------------------------------------------------------------------------
# FIRE cases — multi-tenant vocab present, no isolation strategy
# ---------------------------------------------------------------------------


def test_fires_multi_tenant_no_isolation():
    """Plan with multi-tenant vocabulary but no isolation strategy fires."""
    art = _plan("""
        # Deployment Plan

        ## Deploy to Production

        The service is deployed as a multi-tenant SaaS platform.
        All tenants share a single PostgreSQL database instance.
    """)
    assert PITFALL in _ids(art)


def test_fires_tenant_id_no_isolation():
    """Plan referencing tenant_id with no isolation strategy fires."""
    art = _plan("""
        # Deployment Plan

        ## Deploy to Staging

        Each row in the users table includes a tenant_id foreign key
        to associate records with the correct organization.
    """)
    assert PITFALL in _ids(art)


def test_fires_per_tenant_no_isolation():
    """Plan with per-tenant vocabulary but no isolation strategy fires."""
    art = _plan("""
        # Deployment Plan

        ## Service Architecture

        The API enforces per-tenant rate limits and stores per-tenant
        configuration in a shared configuration table.
    """)
    assert PITFALL in _ids(art)


def test_fires_organization_id_no_isolation():
    """Plan referencing organization_id with no isolation strategy fires."""
    art = _plan("""
        # Deployment Plan

        ## Deploy to Production

        User accounts are scoped by organization_id.
        The application queries records filtered by the caller's org context.
    """)
    assert PITFALL in _ids(art)


def test_fires_saas_platform_no_isolation():
    """Plan for a SaaS platform with no isolation strategy fires."""
    art = _plan("""
        # Deployment Plan

        ## Launch SaaS Platform

        We are launching a SaaS platform serving enterprise customers.
        Customers will sign up and access a shared application tier.
    """)
    assert PITFALL in _ids(art)


# ---------------------------------------------------------------------------
# SILENT cases — isolation strategy present
# ---------------------------------------------------------------------------


def test_silent_row_level_security():
    """Plan with row-level security mentioned is silent."""
    art = _plan("""
        # Deployment Plan

        ## Deploy to Production

        The service is deployed as a multi-tenant SaaS platform.
        Tenant isolation is enforced via row-level security (RLS) policies
        on all tables containing tenant data.
    """)
    assert PITFALL not in _ids(art)


def test_silent_schema_per_tenant():
    """Plan with schema-per-tenant strategy is silent."""
    art = _plan("""
        # Deployment Plan

        ## Deploy to Production

        The service handles multiple tenants. We use a schema-per-tenant
        approach where each tenant has a dedicated PostgreSQL schema.
    """)
    assert PITFALL not in _ids(art)


def test_silent_database_per_tenant():
    """Plan with database-per-tenant strategy is silent."""
    art = _plan("""
        # Deployment Plan

        ## Deploy to Production

        Multi-tenant deployment uses a database-per-tenant model.
        Each enterprise customer receives a dedicated RDS instance.
    """)
    assert PITFALL not in _ids(art)


def test_silent_rls_abbreviation():
    """Plan with RLS abbreviation is silent."""
    art = _plan("""
        # Deployment Plan

        ## Multi-Tenant Architecture

        The application stores data for multiple tenants.
        All queries are gated by RLS policies enforced at the database level.
    """)
    assert PITFALL not in _ids(art)


def test_silent_tenant_isolation_explicit():
    """Plan with explicit tenant isolation mention is silent."""
    art = _plan("""
        # Deployment Plan

        ## Deploy to Production

        Multi-tenant deployment requires strict tenant isolation
        at the data layer to prevent cross-tenant data access.
    """)
    assert PITFALL not in _ids(art)


def test_silent_no_deploy_vocab():
    """Plan with no deployment vocabulary does not fire."""
    art = _plan("""
        # Architecture Notes

        The system is designed as a multi-tenant SaaS platform
        to serve enterprise customers efficiently.
    """)
    assert PITFALL not in _ids(art)


def test_silent_fenced_block():
    """Multi-tenant vocabulary inside a fenced code block does not trigger."""
    art = _plan("""
        # Deployment Plan

        ## Deploy to Production

        We deploy the application to Kubernetes.

        ```yaml
        # multi-tenant deployment config
        # tenant_id filtering applied
        replicas: 3
        ```
    """)
    assert PITFALL not in _ids(art)


def test_silent_heading_only():
    """Multi-tenant vocabulary only in a heading does not trigger."""
    art = _plan("""
        # Multi-Tenant Deployment Plan

        ## Deploy to Production

        The application is deployed to AWS ECS with auto-scaling enabled.
        Health checks are configured on port 8080.
    """)
    assert PITFALL not in _ids(art)


def test_silent_non_plan_artifact():
    """Non-plan artifact does not trigger the check."""
    raw = textwrap.dedent("""
        # Spec

        ## Requirements

        The system shall support multi-tenant deployments with tenant_id isolation.
    """).strip()
    from sddgrade.model import ArtifactType
    art = Artifact(
        path="spec.md",
        type=ArtifactType.SPEC,
        feature_id="test",
        raw=raw,
        sections=parse_sections(raw),
    )
    assert PITFALL not in [f.pitfall_id for f in _plan_no_multi_tenant_isolation(art, CATALOG)]
