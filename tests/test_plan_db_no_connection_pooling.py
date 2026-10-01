"""Tests for PLAN-DB-NO-CONNECTION-POOLING pitfall.

Fires when a plan.md with deployment vocabulary AND relational-database vocabulary
(postgres, mysql, mariadb, aurora, rds, sql server, cockroachdb, tidb, database,
data store, persistent storage) has no connection-pooling strategy mentioned anywhere
in the non-fenced document text.

Source: Amazon Kiro production-readiness checklist; AWS RDS best practices;
        Twelve-Factor App Factor VI Disposability.
"""
from __future__ import annotations

import textwrap

from sddgrade.adapters.base import parse_sections
from sddgrade.catalog import load_catalog
from sddgrade.engine.lint import _plan_db_no_connection_pooling
from sddgrade.model import Artifact, ArtifactType

CATALOG = load_catalog()
PITFALL = "PLAN-DB-NO-CONNECTION-POOLING"


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
    return [f.pitfall_id for f in _plan_db_no_connection_pooling(art, CATALOG)]


# ---------------------------------------------------------------------------
# Firing cases — DB vocab + deploy vocab, no connection-pooling silence token
# ---------------------------------------------------------------------------

def test_fires_postgres_no_pooling():
    """Plan deploys PostgreSQL with no connection-pool strategy."""
    art = _plan("""
        ## Deployment Plan
        We will deploy the service to the production environment.
        The application will connect to a PostgreSQL database on port 5432.
        Credentials will be provided via environment variables.
    """)
    assert _ids(art) == [PITFALL]


def test_fires_mysql_no_pooling():
    """Plan provisions MySQL with no connection-pool mention."""
    art = _plan("""
        ## Production Release
        Release the billing service to production this sprint.
        The service uses MySQL 8.0 as its primary datastore.
        Schema migrations will run via Flyway at startup.
    """)
    assert _ids(art) == [PITFALL]


def test_fires_rds_no_pooling():
    """Plan uses AWS RDS but no connection-pooling strategy."""
    art = _plan("""
        ## Deployment
        Deploy the orders service to the production cluster.
        The service will connect to an AWS RDS Aurora PostgreSQL instance.
        Connection strings will be stored in Secrets Manager.
    """)
    assert _ids(art) == [PITFALL]


def test_fires_database_no_pooling():
    """Plan mentions generic 'database' with deploy vocab but no pooling."""
    art = _plan("""
        ## Release Plan
        Ship the user service to staging and production environments.
        The service connects to the primary database at startup.
        Health checks will validate database connectivity.
    """)
    assert _ids(art) == [PITFALL]


def test_fires_aurora_no_pooling():
    """Plan deploys Aurora but has no connection-pool mention."""
    art = _plan("""
        ## Deployment Plan
        Deploy the analytics service to production.
        Data will be persisted to Amazon Aurora MySQL.
        The service will run as three replicas behind a load balancer.
    """)
    assert _ids(art) == [PITFALL]


def test_fires_cockroachdb_no_pooling():
    """Plan uses CockroachDB with no connection pool strategy."""
    art = _plan("""
        ## Production Deployment
        Roll out the inventory service to the production environment.
        The service uses CockroachDB for distributed storage.
        TLS certificates will be provided by cert-manager.
    """)
    assert _ids(art) == [PITFALL]


# ---------------------------------------------------------------------------
# Silent cases — silence token present or guard not met
# ---------------------------------------------------------------------------

def test_silent_when_pgbouncer_present():
    """'pgbouncer' silences the check."""
    art = _plan("""
        ## Deployment Plan
        Deploy the service to production.
        PostgreSQL connections are managed via PgBouncer in transaction mode.
        Pool size is set to 20 connections per application instance.
    """)
    assert _ids(art) == []


def test_silent_when_connection_pool_present():
    """'connection pool' silences the check."""
    art = _plan("""
        ## Release
        Deploy the API service to production.
        A connection pool of 10 is configured for the MySQL database.
    """)
    assert _ids(art) == []


def test_silent_when_max_connections_present():
    """'max_connections' silences the check."""
    art = _plan("""
        ## Deployment
        Ship the catalog service to production.
        The PostgreSQL RDS instance is configured with max_connections=100.
        Application instances are expected to share the budget.
    """)
    assert _ids(art) == []


def test_silent_when_hikari_present():
    """'hikari' silences the check."""
    art = _plan("""
        ## Production Release
        Deploy the Java service to production.
        Database connections to the PostgreSQL instance use HikariCP with
        maximumPoolSize=10, connectionTimeout=30s.
    """)
    assert _ids(art) == []


def test_silent_when_pool_size_present():
    """'pool_size' silences the check."""
    art = _plan("""
        ## Deployment Plan
        Release the worker service to staging.
        SQLAlchemy engine is configured with pool_size=5, max_overflow=2 for
        the MySQL 8.0 instance.
    """)
    assert _ids(art) == []


def test_silent_when_no_db_vocab():
    """Plan with deploy vocab but no database mention — should not fire."""
    art = _plan("""
        ## Deployment Plan
        Deploy the background worker to the production cluster.
        The worker reads from the internal message queue and calls downstream APIs.
        All state is kept in Redis; no relational data stores are provisioned.
    """)
    assert _ids(art) == []


def test_silent_when_no_deploy_vocab():
    """Plan with database vocab but no deploy guard — should not fire."""
    art = _plan("""
        ## Architecture Overview
        The service uses PostgreSQL for persistence.
        This document describes the data model only; operational concerns are
        covered in a separate plan.
    """)
    assert _ids(art) == []


def test_silent_on_spec_artifact():
    """PLAN-DB-NO-CONNECTION-POOLING must not fire on spec artifacts."""
    art = _spec("""
        ## Deployment Plan
        Deploy the service to production.
        The service connects to a PostgreSQL database.
    """)
    assert _ids(art) == []


def test_silent_when_db_in_fenced_block():
    """Database vocab only inside a fenced code block should not trigger the check."""
    art = _plan("""
        ## Deployment Plan
        We will deploy the service to production this week.
        No new relational data stores are provisioned by this change.

        ```yaml
        # Configuration example
        DATABASE_URL: postgresql://user:pass@localhost:5432/mydb
        MYSQL_HOST: db.example.com
        ```
    """)
    assert _ids(art) == []


def test_silent_when_pgpool_present():
    """'pgpool' silences the check."""
    art = _plan("""
        ## Production Release
        Deploy the reporting service to production.
        All PostgreSQL connections are routed through pgpool-II.
    """)
    assert _ids(art) == []


def test_silent_when_connection_management_present():
    """'connection management' silences the check."""
    art = _plan("""
        ## Deployment Plan
        Ship the order processing service to production.
        The MySQL database connection management strategy uses a 15-connection pool
        per replica instance.
    """)
    assert _ids(art) == []
