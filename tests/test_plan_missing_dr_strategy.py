"""Tests for PLAN-MISSING-DR-STRATEGY pitfall.

Fires when a deployment plan provisions a production relational database
(postgres, mysql, mariadb, aurora, rds, sql server, cockroachdb, tidb, database, db)
with no disaster-recovery vocabulary (DR, RPO, RTO, failover, multi-AZ, etc.).

Sources: Kiro production-readiness checklist; ISO/IEC 25010:2023 Availability;
AWS Well-Architected REL09; CNCF Production Checklist.
"""
from __future__ import annotations

import textwrap

from sddgrade.adapters.base import parse_sections
from sddgrade.catalog import load_catalog
from sddgrade.engine.lint import _plan_missing_dr_strategy
from sddgrade.model import Artifact, ArtifactType

CATALOG = load_catalog()
PITFALL = "PLAN-MISSING-DR-STRATEGY"


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


def _data_model(raw: str) -> Artifact:
    raw = textwrap.dedent(raw).strip()
    return Artifact(
        path="data-model.md",
        type=ArtifactType.DATA_MODEL,
        feature_id="test",
        raw=raw,
        sections=parse_sections(raw),
    )


def _ids(art: Artifact) -> list[str]:
    return [f.pitfall_id for f in _plan_missing_dr_strategy(art, CATALOG)]


# ---------------------------------------------------------------------------
# FIRE cases — plan + relational DB + production + no DR vocab
# ---------------------------------------------------------------------------


def test_fires_postgres_production_no_dr():
    """Plan deploying PostgreSQL to production with no DR vocab fires."""
    art = _plan("""
        # Deployment Plan

        ## Deploy to Production

        1. Provision RDS PostgreSQL 15 instance in us-east-1.
        2. Run database migrations.
        3. Deploy the application to production.
        4. Configure connection pooling via PgBouncer.
    """)
    assert PITFALL in _ids(art)


def test_fires_mysql_production_no_dr():
    """Plan deploying MySQL to production with no DR vocab fires."""
    art = _plan("""
        # Release Plan

        ## Production Release Steps

        1. Launch MySQL 8.0 RDS instance.
        2. Apply schema migrations.
        3. Promote staging to production.
        4. Enable automated backups with 7-day retention.
    """)
    assert PITFALL in _ids(art)


def test_fires_aurora_production_no_dr():
    """Plan deploying Aurora to production with no DR vocab fires."""
    art = _plan("""
        # Deployment Plan

        ## Deployment

        Deploy Aurora cluster to production environment.
        Enable enhanced monitoring.
        Set backup retention to 14 days.
        Configure parameter groups for production workload.
    """)
    assert PITFALL in _ids(art)


def test_fires_database_go_live_no_dr():
    """Plan with 'database' + go-live and no DR fires."""
    art = _plan("""
        # Go-Live Plan

        ## Steps

        1. Provision the production database.
        2. Seed reference data.
        3. Flip DNS to point to production.
        4. Monitor application logs post go-live.
    """)
    assert PITFALL in _ids(art)


def test_fires_rds_prod_deploy_no_dr():
    """Plan with RDS + 'prod deploy' and no DR fires."""
    art = _plan("""
        # Deployment

        ## Prod Deploy

        Provision an RDS instance in the prod VPC.
        Apply security groups from the production template.
        Run the prod deploy pipeline.
    """)
    assert PITFALL in _ids(art)


def test_fires_cockroachdb_production_no_dr():
    """Plan deploying CockroachDB to production with no DR vocab fires."""
    art = _plan("""
        # Release Plan

        ## Deploy to Production

        Provision a CockroachDB cluster in production.
        Initialize the database schema.
        Update DNS records.
        Enable connection pooling.
    """)
    assert PITFALL in _ids(art)


def test_fires_sql_server_production_no_dr():
    """Plan deploying SQL Server to production with no DR fires."""
    art = _plan("""
        # Deployment Plan

        ## Production Deployment

        Deploy SQL Server 2022 on the production host.
        Apply all pending schema migrations.
        Notify stakeholders of the production deployment.
    """)
    assert PITFALL in _ids(art)


# ---------------------------------------------------------------------------
# SILENT cases — DR vocab present, non-relational DB, no prod, fenced, non-plan
# ---------------------------------------------------------------------------


def test_silent_rpo_rto_present():
    """Plan with RPO/RTO defined is silent."""
    art = _plan("""
        # Deployment Plan

        ## Production Deployment

        Provision RDS PostgreSQL in us-east-1 (production).
        Enable Multi-AZ.

        ## DR Strategy

        RPO = 5 minutes via PITR.
        RTO < 30 minutes with automatic failover.
    """)
    assert PITFALL not in _ids(art)


def test_silent_failover_present():
    """Plan mentioning failover is silent."""
    art = _plan("""
        # Deployment Plan

        ## Deploy to Production

        1. Provision RDS MySQL 8.0 in production VPC.
        2. Enable automatic failover to standby instance.
        3. Configure cross-region replica for DR.
    """)
    assert PITFALL not in _ids(art)


def test_silent_multi_az_present():
    """Plan with Multi-AZ configuration is silent."""
    art = _plan("""
        # Production Deployment

        Deploy Aurora PostgreSQL with Multi-AZ enabled.
        Secondary region configured for geo-redundancy.
    """)
    assert PITFALL not in _ids(art)


def test_silent_standby_present():
    """Plan with standby mention is silent."""
    art = _plan("""
        # Deployment

        ## Production

        Provision the PostgreSQL production instance.
        A warm standby replica runs in the secondary region.
        Failover is automated via Route 53 health checks.
    """)
    assert PITFALL not in _ids(art)


def test_silent_no_relational_db():
    """Plan with Redis (non-relational) and no DR vocab is silent — trigger requires relational DB."""
    art = _plan("""
        # Deployment Plan

        ## Deploy to Production

        Provision Redis cluster for session caching in production.
        Enable cluster mode for horizontal scaling.
        Configure eviction policy to allkeys-lru.
    """)
    assert PITFALL not in _ids(art)


def test_silent_no_production_indicator():
    """Plan with PostgreSQL but no production/go-live indicator is silent."""
    art = _plan("""
        # Deployment Plan

        ## Staging Setup

        Provision PostgreSQL 15 in the staging environment.
        Apply migrations.
        Run integration tests against the database.
    """)
    assert PITFALL not in _ids(art)


def test_silent_non_plan_artifact_spec():
    """Spec artifact with database + production language does not fire."""
    art = _spec("""
        # Feature Specification

        ## Functional Requirements

        FR-001: The system shall provision a PostgreSQL production database.
        FR-002: The database shall meet production SLA requirements.
        FR-003: The system shall define RPO and RTO for all database deployments.
    """)
    assert PITFALL not in _ids(art)


def test_silent_non_plan_artifact_data_model():
    """Data-model artifact does not fire."""
    art = _data_model("""
        # Data Model

        ## User

        | Field | Type | Notes |
        |-------|------|-------|
        | id | UUID | primary key |
        | name | text | production display name |

        Deploy this schema to the production database.
    """)
    assert PITFALL not in _ids(art)


def test_silent_db_in_fenced_block():
    """DB vocab inside a fenced code block does not trigger."""
    art = _plan("""
        # Deployment Plan

        ## Production Deployment

        Run the following command to verify connectivity:

        ```bash
        psql -h production-db.example.com -U admin -d mydb -c "SELECT 1"
        ```

        All data is stored in object storage only.
        No persistent relational store is provisioned.
    """)
    assert PITFALL not in _ids(art)


def test_silent_db_on_heading_line():
    """DB vocab appearing only in a heading line does not trigger."""
    art = _plan("""
        # Deployment Plan

        ## Production Database Notes

        Connect to the production environment.
        Deploy the application container.
        Monitor production metrics.
    """)
    assert PITFALL not in _ids(art)


def test_silent_recovery_point_present():
    """Plan with 'recovery point' mention is silent."""
    art = _plan("""
        # Production Deployment Plan

        Deploy the production PostgreSQL database.
        Recovery point objective is 15 minutes.
        The recovery time target is under 1 hour.
    """)
    assert PITFALL not in _ids(art)


def test_silent_geo_redundancy_present():
    """Plan with geo-redundancy is silent."""
    art = _plan("""
        # Production Deployment

        Provision RDS MariaDB production instance.
        Geo-redundancy is provided by Aurora Global Database.
    """)
    assert PITFALL not in _ids(art)
