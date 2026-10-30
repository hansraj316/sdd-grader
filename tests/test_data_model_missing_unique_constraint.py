"""Tests for DATA-MODEL-MISSING-UNIQUE-CONSTRAINT pitfall.

Fires when a data-model entity contains uniqueness-sensitive fields
(email, username, slug, sku, serial_number, external_id, handle, login,
phone_number) but no unique-constraint annotation in its body.

Sources: ISO/IEC 27001:2022 A.8.10; GDPR Art.5(1)(d); MAQA entity completeness.
"""
from __future__ import annotations

import textwrap

from sddgrade.adapters.base import parse_sections
from sddgrade.catalog import load_catalog
from sddgrade.engine.lint import _data_model_missing_unique_constraint
from sddgrade.model import Artifact, ArtifactType

CATALOG = load_catalog()
PITFALL = "DATA-MODEL-MISSING-UNIQUE-CONSTRAINT"


def _dm(raw: str) -> Artifact:
    raw = textwrap.dedent(raw).strip()
    return Artifact(
        path="data-model.md",
        type=ArtifactType.DATA_MODEL,
        feature_id="test",
        raw=raw,
        sections=parse_sections(raw),
    )


def _ids(art: Artifact) -> list[str]:
    return [f.pitfall_id for f in _data_model_missing_unique_constraint(art, CATALOG)]


# ---------------------------------------------------------------------------
# Firing cases
# ---------------------------------------------------------------------------


def test_fires_email_no_unique():
    """Entity has email field but no unique constraint."""
    art = _dm("""
        # Data Model

        ### User

        | Field     | Type         | Notes        |
        |-----------|--------------|--------------|
        | id        | UUID         | PK           |
        | email     | VARCHAR(255) | NOT NULL     |
        | name      | VARCHAR(100) |              |
        | created_at | timestamp   | audit        |
    """)
    assert PITFALL in _ids(art)


def test_fires_username_no_unique():
    """Entity has username field but no unique annotation."""
    art = _dm("""
        # Data Model

        ### Account

        | Field     | Type    | Notes   |
        |-----------|---------|---------|
        | id        | integer | PK      |
        | username  | text    | login   |
        | password  | text    |         |
    """)
    assert PITFALL in _ids(art)


def test_fires_slug_no_unique():
    """Entity has slug field but no unique constraint."""
    art = _dm("""
        # Data Model

        ### Article

        - id: UUID (PK)
        - slug: string — URL-friendly name
        - title: string
        - body: text
        - created_at: timestamp
    """)
    assert PITFALL in _ids(art)


def test_fires_sku_no_unique():
    """Entity has sku field but no unique annotation."""
    art = _dm("""
        # Data Model

        ### Product

        | Field       | Type    | Notes       |
        |-------------|---------|-------------|
        | id          | UUID    | PK          |
        | sku         | text    | product code|
        | name        | text    |             |
        | price       | decimal |             |
    """)
    assert PITFALL in _ids(art)


def test_fires_login_no_unique():
    """Entity has login field but no unique constraint."""
    art = _dm("""
        # Data Model

        ### Member

        - id: integer (PK)
        - login: varchar(50)
        - email: varchar(255)
        - created_at: timestamp
    """)
    assert PITFALL in _ids(art)


# ---------------------------------------------------------------------------
# Silent cases
# ---------------------------------------------------------------------------


def test_silent_email_with_unique_keyword():
    """Entity has email field AND 'UNIQUE' annotation — no finding."""
    art = _dm("""
        # Data Model

        ### User

        | Field | Type         | Notes            |
        |-------|--------------|------------------|
        | id    | UUID         | PK               |
        | email | VARCHAR(255) | NOT NULL, UNIQUE  |
        | name  | VARCHAR(100) |                  |
    """)
    assert PITFALL not in _ids(art)


def test_silent_username_with_unique_constraint():
    """Entity documents unique constraint explicitly."""
    art = _dm("""
        # Data Model

        ### Account

        | Field    | Type | Notes |
        |----------|------|-------|
        | id       | int  | PK    |
        | username | text |       |

        Constraints: unique constraint on username (uk_accounts_username).
    """)
    assert PITFALL not in _ids(art)


def test_silent_slug_with_unique_index():
    """Entity has slug AND 'unique index' annotation."""
    art = _dm("""
        # Data Model

        ### Post

        - id: UUID (PK)
        - slug: string — unique index: idx_posts_slug
        - title: string
    """)
    assert PITFALL not in _ids(art)


def test_silent_no_unique_sensitive_fields():
    """Entity has no uniqueness-sensitive fields — should not fire."""
    art = _dm("""
        # Data Model

        ### Order

        | Field      | Type      | Notes    |
        |------------|-----------|----------|
        | id         | UUID      | PK       |
        | user_id    | UUID      | FK       |
        | status     | enum      |          |
        | created_at | timestamp | audit    |
    """)
    assert PITFALL not in _ids(art)


def test_silent_spec_artifact():
    """Check does not apply to non-data-model artifact types."""
    raw = textwrap.dedent("""
        # Spec

        ### User

        - email field required
        - username field
    """).strip()
    art = Artifact(
        path="spec.md",
        type=ArtifactType.SPEC,
        feature_id="test",
        raw=raw,
        sections=parse_sections(raw),
    )
    assert PITFALL not in _ids(art)


def test_silent_uk_prefix_in_constraint():
    """Entity uses 'uk_' prefix naming convention — silence applies."""
    art = _dm("""
        # Data Model

        ### Customer

        | Field    | Type    | Constraints            |
        |----------|---------|------------------------|
        | id       | int     | PK                     |
        | email    | text    | uk_customer_email       |
        | username | text    | uk_customer_username    |
    """)
    assert PITFALL not in _ids(art)


def test_silent_external_id_with_uniqueness_keyword():
    """Entity with external_id field that documents uniqueness."""
    art = _dm("""
        # Data Model

        ### Integration

        - id: UUID (PK)
        - external_id: string — uniqueness enforced by application layer
        - provider: string
    """)
    assert PITFALL not in _ids(art)
