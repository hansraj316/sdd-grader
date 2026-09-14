"""Tests for PLAN-NO-DATA-RETENTION pitfall.

Fires when a plan document mentions persistent storage in ≥2 non-fenced lines
but has no data-retention / TTL / purge / archival vocabulary anywhere.
Guard: ≥2 non-fenced storage-vocab matches required.
Silence: any retention/TTL/purge/archival token anywhere in the document.
Applies to plan artifacts only; silent on spec and tasks.
"""

from __future__ import annotations

import textwrap

from sddgrade.adapters.base import parse_sections
from sddgrade.catalog import load_catalog
from sddgrade.engine.lint import _plan_no_data_retention
from sddgrade.model import Artifact, ArtifactType

CATALOG = load_catalog()
PITFALL = "PLAN-NO-DATA-RETENTION"


def _plan(raw: str) -> Artifact:
    raw = textwrap.dedent(raw).strip()
    sections = parse_sections(raw)
    return Artifact(
        path="plan.md",
        type=ArtifactType.PLAN,
        raw=raw,
        sections=sections,
    )


def _spec(raw: str) -> Artifact:
    raw = textwrap.dedent(raw).strip()
    sections = parse_sections(raw)
    return Artifact(
        path="spec.md",
        type=ArtifactType.SPEC,
        raw=raw,
        sections=sections,
    )


def _tasks(raw: str) -> Artifact:
    raw = textwrap.dedent(raw).strip()
    sections = parse_sections(raw)
    return Artifact(
        path="tasks.md",
        type=ArtifactType.TASKS,
        raw=raw,
        sections=sections,
    )


def _fires(art: Artifact) -> bool:
    findings = _plan_no_data_retention(art, CATALOG)
    return any(f.pitfall_id == PITFALL for f in findings)


# ---------------------------------------------------------------------------
# FIRE cases (≥2 storage mentions, no retention vocab)
# ---------------------------------------------------------------------------

class TestFires:
    def test_postgres_and_redis_no_retention(self):
        """Plan with PostgreSQL + Redis mentions but no TTL/purge → fires."""
        art = _plan("""\
            ## Architecture
            User data is stored in PostgreSQL.
            Session tokens are cached in Redis.
            ## Deployment
            Deploy with Docker Compose.
        """)
        assert _fires(art)

    def test_s3_and_database_no_retention(self):
        """Plan with S3 + database mentions and no archival policy → fires."""
        art = _plan("""\
            ## Storage
            Uploaded files are stored in S3.
            Metadata is persisted in the database.
            ## Deployment
            Run `docker compose up`.
        """)
        assert _fires(art)

    def test_blob_and_table_no_retention(self):
        """Plan with blob storage + table mentions and no lifecycle → fires."""
        art = _plan("""\
            ## Data Layer
            Attachments go into blob storage.
            User records are written to the users table.
            ## API
            REST endpoints expose CRUD operations.
        """)
        assert _fires(art)

    def test_event_store_and_logs_no_retention(self):
        """Event store + logs with no purge/rotation policy → fires."""
        art = _plan("""\
            ## Events
            Domain events are written to the event-store.
            Application logs are shipped to the logging service.
            ## Monitoring
            Grafana dashboards display system health.
        """)
        assert _fires(art)

    def test_mongodb_and_cassandra_no_retention(self):
        """MongoDB + Cassandra with no data lifecycle → fires."""
        art = _plan("""\
            ## Persistence
            Documents are stored in MongoDB.
            Time-series data is stored in Cassandra.
        """)
        assert _fires(art)

    def test_fires_at_line_1(self):
        """Finding is anchored at line 1."""
        art = _plan("""\
            ## Plan
            We use PostgreSQL for relational data.
            Blobs are stored in S3.
        """)
        findings = _plan_no_data_retention(art, CATALOG)
        matches = [f for f in findings if f.pitfall_id == PITFALL]
        assert matches
        assert matches[0].line == 1


# ---------------------------------------------------------------------------
# SILENT cases
# ---------------------------------------------------------------------------

class TestSilent:
    def test_silent_with_ttl_statement(self):
        """Retention present via TTL → silent."""
        art = _plan("""\
            ## Storage
            Session tokens are stored in Redis with a TTL of 24 hours.
            User data is stored in PostgreSQL.
        """)
        assert not _fires(art)

    def test_silent_with_purge_schedule(self):
        """Retention present via purge → silent."""
        art = _plan("""\
            ## Data Layer
            Events are stored in PostgreSQL and purged after 90 days.
            Uploads land in S3.
        """)
        assert not _fires(art)

    def test_silent_with_archival_policy(self):
        """Retention present via archival → silent."""
        art = _plan("""\
            ## Storage
            Logs are written to the database.
            S3 objects are archived to Glacier after 30 days.
        """)
        assert not _fires(art)

    def test_silent_with_retention_period_keyword(self):
        """Explicit 'retention' keyword → silent."""
        art = _plan("""\
            ## Persistence
            User records in PostgreSQL.
            Blobs in S3.
            ## Data Lifecycle
            The retention period for all records is 7 years per legal requirement.
        """)
        assert not _fires(art)

    def test_silent_with_deletion_policy(self):
        """Explicit 'deletion policy' → silent."""
        art = _plan("""\
            ## Storage
            Events are stored in the event-store (append-only log).
            User table in PostgreSQL.
            Our deletion policy removes stale records after 365 days.
        """)
        assert not _fires(art)

    def test_silent_with_rotate_logs(self):
        """Log rotation counts as a lifecycle statement → silent."""
        art = _plan("""\
            ## Observability
            Application logs are written to the logs directory.
            We rotate logs weekly and delete entries older than 30 days.
            ## Storage
            Database stores user records.
        """)
        assert not _fires(art)

    def test_silent_single_storage_mention(self):
        """Only one storage mention — below guard threshold → silent."""
        art = _plan("""\
            ## Architecture
            We use PostgreSQL.
            ## API
            REST API with JSON payloads.
        """)
        assert not _fires(art)

    def test_silent_storage_in_fenced_block(self):
        """Storage vocab only in fenced code block → below threshold → silent."""
        art = _plan("""\
            ## Setup
            Run the database:
            ```bash
            docker run postgres
            docker run redis
            ```
            Configure the app.
        """)
        assert not _fires(art)

    def test_silent_spec_artifact(self):
        """Check is silent on spec artifacts."""
        art = _spec("""\
            ## Requirements
            FR-001: The system shall store records in PostgreSQL.
            FR-002: Logs shall be written to S3.
        """)
        assert not _fires(art)

    def test_silent_tasks_artifact(self):
        """Check is silent on tasks artifacts."""
        art = _tasks("""\
            ## Tasks
            - [ ] T001 Set up PostgreSQL database
            - [ ] T002 Configure S3 bucket
        """)
        assert not _fires(art)

    def test_silent_auto_delete_keyword(self):
        """auto-delete counts as retention policy → silent."""
        art = _plan("""\
            ## Storage
            Temporary data stored in Redis.
            User uploads persisted in the database.
            Redis keys auto-delete after session ends.
        """)
        assert not _fires(art)

    def test_silent_expiration_keyword(self):
        """expiration counts as retention policy → silent."""
        art = _plan("""\
            ## Caching
            Cache entries stored in Redis.
            User sessions persisted in PostgreSQL.
            Cache keys have an expiration of 1 hour.
        """)
        assert not _fires(art)

    def test_silent_time_to_live_phrase(self):
        """'time-to-live' phrase counts as retention → silent."""
        art = _plan("""\
            ## Storage
            Events are written to the database.
            Bucket stores uploaded files in S3.
            All cached items have a time-to-live of 6 hours.
        """)
        assert not _fires(art)

    def test_silent_data_lifecycle_heading(self):
        """'data lifecycle' counts as retention signal → silent."""
        art = _plan("""\
            ## Storage
            User table in PostgreSQL.
            Logs in S3.
            ## Data Lifecycle
            All data follows our standard lifecycle management process.
        """)
        assert not _fires(art)
