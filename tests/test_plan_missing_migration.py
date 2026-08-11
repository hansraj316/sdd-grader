"""Tests for PLAN-MISSING-MIGRATION — plans that mention schema changes but lack a data-migration strategy."""
from __future__ import annotations

import textwrap

from sddgrade.adapters.base import parse_sections
from sddgrade.catalog import load_catalog
from sddgrade.engine.lint import _plan_missing_migration
from sddgrade.model import Artifact, ArtifactType

CATALOG = load_catalog()
PITFALL = "PLAN-MISSING-MIGRATION"


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
    return [f.pitfall_id for f in _plan_missing_migration(art, CATALOG)]


# ------------------------------------------------------------------ fires cases

def test_fires_on_alter_table_no_migration():
    """Plan uses ALTER TABLE but provides no migration strategy."""
    art = _plan("""
        ## Schema Changes

        We will alter table users to add a `verified_at` timestamp column.
        This ensures account verification state is persisted.
    """)
    assert PITFALL in _ids(art)


def test_fires_on_add_column_no_migration():
    """Plan mentions adding a column but no migration tool or script."""
    art = _plan("""
        ## Database Design

        Add column `last_login` to the sessions table to track activity.
        Deploy after the cache warm-up is complete.
    """)
    assert PITFALL in _ids(art)


def test_fires_on_new_table_no_migration():
    """Plan mentions creating a new table with no migration vocabulary."""
    art = _plan("""
        ## Technical Design

        Create a new table `audit_log` to store user-action events.
        The table will have a composite primary key on (user_id, created_at).
    """)
    assert PITFALL in _ids(art)


def test_fires_on_drop_column_no_migration():
    """Plan mentions dropping a column with no data-migration strategy."""
    art = _plan("""
        ## Cleanup

        Drop column `legacy_token` from the users table.
        Run during the maintenance window.
    """)
    assert PITFALL in _ids(art)


def test_fires_on_rename_column_no_migration():
    """Plan mentions renaming a column but no migration step."""
    art = _plan("""
        ## Refactoring

        Rename column `user_name` to `username` in the accounts table.
        Update all ORM references accordingly.
    """)
    assert PITFALL in _ids(art)


def test_fires_on_db_migration_guard_no_strategy():
    """Plan mentions 'db migration' as a task but has no strategy vocabulary."""
    art = _plan("""
        ## Steps

        1. Run db migration to add the new schema change.
        2. Restart the application server.
    """)
    assert PITFALL in _ids(art)


def test_fires_on_add_index_no_migration():
    """Plan mentions adding an index with no migration tooling mentioned."""
    art = _plan("""
        ## Performance

        Add index on the `created_at` column of the events table.
        This query is currently doing a full-table scan.
    """)
    assert PITFALL in _ids(art)


# ------------------------------------------------------------------ silent cases

def test_silent_when_alembic_mentioned():
    """Plan mentions schema change and also mentions Alembic."""
    art = _plan("""
        ## Database Changes

        Add column `verified_at` to users.
        Run `alembic upgrade head` before the service restart.
    """)
    assert PITFALL not in _ids(art)


def test_silent_when_flyway_mentioned():
    """Plan references Flyway for schema migration."""
    art = _plan("""
        ## Migration Strategy

        Alter table orders to add a `fulfilled_at` column.
        Flyway will apply V2__add_fulfilled_at.sql on startup.
    """)
    assert PITFALL not in _ids(art)


def test_silent_when_migration_script_mentioned():
    """Plan mentions a migration script alongside schema changes."""
    art = _plan("""
        ## Schema

        Add column `retry_count` to the jobs table.
        A migration script will backfill existing rows to 0.
    """)
    assert PITFALL not in _ids(art)


def test_silent_when_data_migration_mentioned():
    """Plan mentions data migration explicitly."""
    art = _plan("""
        ## Implementation

        Create a new table `feature_flags`.
        The data migration will copy existing config rows to the new table.
    """)
    assert PITFALL not in _ids(art)


def test_silent_when_up_sql_mentioned():
    """Plan references up.sql migration file."""
    art = _plan("""
        ## Schema Changes

        Rename column `old_id` to `external_id` in partners.
        Apply up.sql in the deployment pipeline before traffic switch.
    """)
    assert PITFALL not in _ids(art)


def test_silent_when_no_schema_change_vocab():
    """Pure feature plan with no schema-change vocabulary — guard silent."""
    art = _plan("""
        ## Implementation

        Add a caching layer in front of the product listing endpoint.
        No database changes are required.
    """)
    assert PITFALL not in _ids(art)


def test_silent_when_schema_change_in_fenced_block():
    """ALTER TABLE inside a fenced code block does not trigger the guard."""
    art = _plan("""
        ## Reference

        The existing migration is documented below:

        ```sql
        ALTER TABLE users ADD COLUMN legacy_id INTEGER;
        ```

        This plan adds no further schema changes.
    """)
    assert PITFALL not in _ids(art)


def test_silent_on_spec_artifact():
    """Check does not fire on spec artifacts."""
    raw = textwrap.dedent("""
        ## Schema

        Add column `verified_at` to users with no migration strategy.
    """).strip()
    spec = Artifact(
        path="spec.md",
        type=ArtifactType.SPEC,
        feature_id="test",
        raw=raw,
        sections=parse_sections(raw),
    )
    assert PITFALL not in [f.pitfall_id for f in _plan_missing_migration(spec, CATALOG)]
