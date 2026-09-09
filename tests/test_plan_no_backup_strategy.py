"""Tests for PLAN-NO-BACKUP-STRATEGY pitfall.

Fires when a plan.md with deployment vocabulary AND a database or persistent
data-store mention has no backup/restore/disaster-recovery vocabulary anywhere
in the document.

Sources: ISO/IEC 25010:2023 §4.2.1.4 Fault Tolerance / Availability;
         AWS Well-Architected Reliability Pillar REL-9 (Back Up Data);
         Amazon Kiro production-readiness checklist;
         Google SRE Book — Chapter 26: Data Integrity.
"""
from __future__ import annotations

import textwrap

from sddgrade.adapters.base import parse_sections
from sddgrade.catalog import load_catalog
from sddgrade.engine.lint import _plan_no_backup_strategy
from sddgrade.model import Artifact, ArtifactType

CATALOG = load_catalog()
PITFALL = "PLAN-NO-BACKUP-STRATEGY"


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
    return [f.pitfall_id for f in _plan_no_backup_strategy(art, CATALOG)]


# ---------------------------------------------------------------------------
# Firing cases — database vocab present, no backup/recovery token
# ---------------------------------------------------------------------------


def test_fires_postgres_no_backup():
    """Plan mentions PostgreSQL with deploy vocab but no backup strategy."""
    art = _plan("""
        ## Deployment Plan
        Deploy version 2.0 to production.
        The service uses PostgreSQL 15 for persistent data storage.
        No data protection strategy is documented in this plan.
    """)
    assert PITFALL in _ids(art)


def test_fires_rds_no_recovery():
    """Plan provisions an RDS instance with no backup mention."""
    art = _plan("""
        ## Release Plan
        Deploy the new billing service to AWS production.
        Provision an RDS PostgreSQL instance in us-east-1.
        Security groups restrict access to the application tier only.
    """)
    assert PITFALL in _ids(art)


def test_fires_mysql_no_restore():
    """Plan mentions MySQL database with no restore procedure."""
    art = _plan("""
        ## Production Deployment
        Release the legacy reporting service to production.
        The service connects to a MySQL 8.0 database on the primary host.
        Data durability and high availability are outside the scope of this plan.
    """)
    assert PITFALL in _ids(art)


def test_fires_mongodb_no_pitr():
    """Plan uses MongoDB with no point-in-time recovery mention."""
    art = _plan("""
        ## Deployment Plan
        Deploy the analytics service to the production Kubernetes cluster.
        The service stores events in a MongoDB cluster.
        Rolling deployment with zero-downtime upgrade is used.
    """)
    assert PITFALL in _ids(art)


def test_fires_dynamodb_no_backup():
    """Plan provisions DynamoDB table with no backup strategy."""
    art = _plan("""
        ## Release Plan
        Deploy the notification service to AWS.
        Create a new DynamoDB table for device tokens.
        IAM policies restrict write access to the service role only.
    """)
    assert PITFALL in _ids(art)


def test_fires_persistent_volume_no_backup():
    """Plan mounts a persistent volume with no backup/snapshot mention."""
    art = _plan("""
        ## Deployment Plan
        Deploy the file-processing service to the production cluster.
        Mount a persistent volume at /data for intermediate results.
        The service reads and writes large binary files during processing.
    """)
    assert PITFALL in _ids(art)


def test_fires_database_keyword_no_strategy():
    """Plan says 'database' with no backup or recovery strategy."""
    art = _plan("""
        ## Production Deployment
        Deploy the user-management service to production.
        The service depends on the shared database provisioned by the platform team.
        Health checks confirm the database connection before routing traffic.
    """)
    assert PITFALL in _ids(art)


# ---------------------------------------------------------------------------
# Silent cases — backup/recovery vocabulary present
# ---------------------------------------------------------------------------


def test_silent_backup_mentioned():
    """Plan mentions 'backup' — silenced."""
    art = _plan("""
        ## Deployment Plan
        Deploy the API to production.
        The service uses PostgreSQL 15 for persistent storage.
        Daily automated backup is configured with a 30-day retention window.
    """)
    assert PITFALL not in _ids(art)


def test_silent_pg_dump_mentioned():
    """Plan describes pg_dump for backup — silenced."""
    art = _plan("""
        ## Release Plan
        Deploy the reporting service to production.
        The PostgreSQL database is backed up nightly via pg_dump to S3.
        Restore procedures are documented in the runbook.
    """)
    assert PITFALL not in _ids(art)


def test_silent_snapshot_mentioned():
    """Plan uses snapshots for the RDS instance — silenced."""
    art = _plan("""
        ## Production Deployment
        Provision an RDS Aurora cluster in eu-west-1.
        Automated snapshots are enabled with a 7-day retention window.
        Cross-region snapshot copy is scheduled weekly for disaster recovery.
    """)
    assert PITFALL not in _ids(art)


def test_silent_pitr_enabled():
    """Plan enables point-in-time recovery for DynamoDB — silenced."""
    art = _plan("""
        ## Release Plan
        Deploy the notification service to production.
        Create a DynamoDB table for device tokens with point-in-time recovery enabled.
        RPO is 5 minutes; RTO is less than 1 hour.
    """)
    assert PITFALL not in _ids(art)


def test_silent_rto_rpo_stated():
    """Plan explicitly states RPO and RTO — silenced."""
    art = _plan("""
        ## Deployment Plan
        Deploy the payment service to production.
        The service uses MySQL 8 for transaction records.
        RPO=0 for committed transactions; RTO<1 h via automated restore from replica.
    """)
    assert PITFALL not in _ids(art)


def test_silent_disaster_recovery_section():
    """Plan has disaster recovery vocabulary — silenced."""
    art = _plan("""
        ## Production Deployment
        Deploy the data-processing service to production.
        PostgreSQL stores raw ingestion records.
        Disaster recovery is handled by the platform team's cross-region replication.
    """)
    assert PITFALL not in _ids(art)


def test_silent_cross_region_mentioned():
    """Plan describes cross-region replication — silenced."""
    art = _plan("""
        ## Deployment Plan
        Deploy the search service to production.
        Elasticsearch cluster data is replicated via cross-region snapshot to eu-west-1.
        Shards are distributed across availability zones for fault tolerance.
    """)
    assert PITFALL not in _ids(art)


def test_silent_failover_mentioned():
    """Plan describes failover strategy — silenced."""
    art = _plan("""
        ## Release Plan
        Deploy the payments service to production with high availability.
        RDS Multi-AZ deployment provides automatic failover in under 60 seconds.
        Connection pooling is configured to retry on connection errors.
    """)
    assert PITFALL not in _ids(art)


def test_silent_no_database_vocab():
    """Plan has deploy vocab but no database/persistent-store mention — not applicable."""
    art = _plan("""
        ## Deployment Plan
        Deploy the frontend bundle to the CDN via GitHub Actions.
        All files are static; no server-side state is stored.
        Cache invalidation is performed after each deploy.
    """)
    assert PITFALL not in _ids(art)


def test_silent_no_deploy_vocab():
    """No deployment vocabulary — deploy guard prevents false positive."""
    art = _plan("""
        ## Engineering Notes
        Consider using PostgreSQL for the new analytics feature.
        This document covers general design patterns only.
    """)
    assert PITFALL not in _ids(art)


def test_silent_spec_artifact():
    """Check does not apply to spec artifacts — skipped."""
    art = _spec("""
        ## Deployment Plan
        Deploy the user service to production.
        The system shall use PostgreSQL for persistent storage.
        No backup strategy is defined in this specification.
    """)
    assert PITFALL not in _ids(art)


def test_silent_fenced_db_only():
    """Database vocabulary only inside a fenced code block — not a trigger."""
    art = _plan("""
        ## Deployment Plan
        Deploy the API to production.

        ```yaml
        env:
          DATABASE_URL: postgres://db:5432/app
          REDIS_URL: redis://cache:6379
        ```

        All credentials are injected via environment variables from Vault.
        Daily backup is configured for all persistent data stores.
    """)
    assert PITFALL not in _ids(art)


def test_fires_once_aggregate():
    """Multiple database references fire only one finding."""
    art = _plan("""
        ## Deployment Plan
        Deploy the data pipeline service to production.
        The pipeline reads from a PostgreSQL source database.
        Results are stored in a MySQL target database.
        No data protection strategy is described in this plan.
    """)
    findings = _plan_no_backup_strategy(art, CATALOG)
    assert len([f for f in findings if f.pitfall_id == PITFALL]) == 1
