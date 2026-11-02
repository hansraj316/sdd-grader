"""Tests for DATA-MODEL-MISSING-FIELD-TYPES pitfall.

Fires when a data-model entity table has attribute rows but zero rows contain a
recognised data type token (varchar, string, text, integer, int, bigint, smallint,
float, double, decimal, numeric, boolean, bool, uuid, date, datetime, timestamp,
timestamptz, json, jsonb, bytes, blob, enum, array, serial, bigserial).

Sources: ISO/IEC 25010:2023 data quality; Kiro entity specification; Canon Volere
data dictionary standard.
"""
from __future__ import annotations

import textwrap

from sddgrade.adapters.base import parse_sections
from sddgrade.catalog import load_catalog
from sddgrade.engine.lint import _data_model_missing_field_types
from sddgrade.model import Artifact, ArtifactType

CATALOG = load_catalog()
PITFALL = "DATA-MODEL-MISSING-FIELD-TYPES"


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
    return [f.pitfall_id for f in _data_model_missing_field_types(art, CATALOG)]


# ---------------------------------------------------------------------------
# Firing cases — entity table with no type annotations
# ---------------------------------------------------------------------------


def test_fires_bare_field_names_no_types():
    """Entity table with only field names and no type column fires."""
    art = _dm("""
        # Data Model

        ### User

        | Field      | Notes        |
        |------------|--------------|
        | id         | Primary key  |
        | name       | Display name |
        | email      | Login email  |
    """)
    assert PITFALL in _ids(art)


def test_fires_type_column_header_only():
    """Header row says 'Type' but data rows have no recognised type tokens."""
    art = _dm("""
        # Data Model

        ### Order

        | Field      | Type    | Notes       |
        |------------|---------|-------------|
        | id         | PK      | Primary key |
        | user_id    | FK      | References  |
        | status     | see doc | TBD         |
    """)
    assert PITFALL in _ids(art)


def test_fires_multiple_entities_missing_types():
    """Two entities with no types → single finding listing both."""
    art = _dm("""
        # Data Model

        ### Product

        | Field  | Notes |
        |--------|-------|
        | id     | PK    |
        | name   | title |

        ### Category

        | Field | Description |
        |-------|-------------|
        | id    | PK          |
        | label | display     |
    """)
    findings = _data_model_missing_field_types(art, CATALOG)
    assert len(findings) == 1
    assert PITFALL in [f.pitfall_id for f in findings]
    msg = findings[0].message
    assert "Product" in msg
    assert "Category" in msg


def test_fires_notes_only_no_type_token():
    """Entity table with description-only rows and no type vocab fires."""
    art = _dm("""
        # Data Model

        ### Session

        | Attribute  | Description              |
        |------------|--------------------------|
        | session_id | Unique session ID        |
        | user_id    | Owner of session         |
        | expires    | When session expires     |
    """)
    assert PITFALL in _ids(art)


# ---------------------------------------------------------------------------
# Silent cases — entity table with type annotations present
# ---------------------------------------------------------------------------


def test_silent_varchar_type():
    """Entity table with VARCHAR type annotation is silent."""
    art = _dm("""
        # Data Model

        ### User

        | Field | Type         | Notes        |
        |-------|--------------|--------------|
        | id    | UUID         | Primary key  |
        | name  | VARCHAR(255) | Display name |
    """)
    assert PITFALL not in _ids(art)


def test_silent_integer_type():
    """Entity table with INTEGER annotation is silent."""
    art = _dm("""
        # Data Model

        ### Counter

        | Field | Type    | Notes |
        |-------|---------|-------|
        | id    | INTEGER | PK    |
        | count | INTEGER | tally |
    """)
    assert PITFALL not in _ids(art)


def test_silent_timestamp_type():
    """Entity table with TIMESTAMP annotation is silent."""
    art = _dm("""
        # Data Model

        ### Audit

        | Field      | Type      | Notes       |
        |------------|-----------|-------------|
        | id         | UUID      | PK          |
        | created_at | TIMESTAMP | When created|
    """)
    assert PITFALL not in _ids(art)


def test_silent_boolean_type():
    """Entity table with BOOLEAN annotation is silent."""
    art = _dm("""
        # Data Model

        ### Flag

        | Field   | Type    | Notes      |
        |---------|---------|------------|
        | id      | INT     | PK         |
        | enabled | BOOLEAN | Active flag|
    """)
    assert PITFALL not in _ids(art)


def test_silent_json_type():
    """Entity table with JSON annotation is silent."""
    art = _dm("""
        # Data Model

        ### Config

        | Field   | Type | Notes    |
        |---------|------|----------|
        | id      | UUID | PK       |
        | payload | JSON | Settings |
    """)
    assert PITFALL not in _ids(art)


def test_silent_entity_with_no_table():
    """Entity with no table rows at all is skipped (no finding)."""
    art = _dm("""
        # Data Model

        ### Event

        Stores event data as a streaming log.
        No tabular schema defined yet.
    """)
    assert PITFALL not in _ids(art)


def test_silent_fenced_code_block():
    """Table rows inside a fenced code block are ignored."""
    art = _dm("""
        # Data Model

        ### Example

        ```sql
        | id   | name  |
        |------|-------|
        | 1    | Alice |
        ```
    """)
    assert PITFALL not in _ids(art)


def test_silent_non_data_model_artifact():
    """Check does not fire on non-data-model artifacts."""
    from sddgrade.model import ArtifactType as AT
    raw = textwrap.dedent("""
        # Spec

        ### User

        | Field | Notes |
        |-------|-------|
        | id    | PK    |
    """).strip()
    art = Artifact(
        path="spec.md",
        type=AT.SPEC,
        feature_id="test",
        raw=raw,
        sections=parse_sections(raw),
    )
    assert PITFALL not in [f.pitfall_id for f in _data_model_missing_field_types(art, CATALOG)]


def test_silent_partial_types_silences_entity():
    """If at least one row has a type token, entity is not flagged."""
    art = _dm("""
        # Data Model

        ### Mixed

        | Field   | Type    | Notes    |
        |---------|---------|----------|
        | id      | UUID    | PK       |
        | extra   | no type | freetext |
    """)
    assert PITFALL not in _ids(art)
