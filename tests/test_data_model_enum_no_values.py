"""Tests for DATA-MODEL-ENUM-NO-VALUES pitfall.

Fires when a data-model pipe-delimited table row has a cell matching \\benum\\b
(case-insensitive) and neither that cell nor the last cell in the row contains
a value-separator ('/', ',', or '(').  One finding per offending row.

Sources: ISO/IEC/IEEE 29148:2018 §5.2.5 (completeness); data-modeling best practice.
"""
from __future__ import annotations

import textwrap

from sddgrade.adapters.base import parse_sections
from sddgrade.catalog import load_catalog
from sddgrade.engine.lint import _data_model_enum_no_values
from sddgrade.model import Artifact, ArtifactType

CATALOG = load_catalog()
PITFALL = "DATA-MODEL-ENUM-NO-VALUES"


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
    return [f.pitfall_id for f in _data_model_enum_no_values(art, CATALOG)]


# ---------------------------------------------------------------------------
# Firing cases — enum field with no value list
# ---------------------------------------------------------------------------


def test_fires_bare_enum_lowercase():
    """Table row with 'enum' type cell and no value separators fires."""
    art = _dm("""
        # Data Model

        ### Order

        | Field  | Type | Notes         |
        |--------|------|---------------|
        | status | enum | Current state |
    """)
    assert PITFALL in _ids(art)


def test_fires_enum_capitalised():
    """'Enum' with capital E should also fire (case-insensitive)."""
    art = _dm("""
        # Data Model

        ### User

        | Field | Type | Notes |
        |-------|------|-------|
        | role  | Enum | TBD   |
    """)
    assert PITFALL in _ids(art)


def test_fires_enum_uppercase():
    """'ENUM' all-caps should also fire."""
    art = _dm("""
        # Data Model

        ### Product

        | Field    | Type | Notes     |
        |----------|------|-----------|
        | category | ENUM | See below |
    """)
    assert PITFALL in _ids(art)


def test_fires_enum_prose_note_no_separator():
    """Enum field with a prose note that has no separator still fires."""
    art = _dm("""
        # Data Model

        ### Ticket

        | Field    | Type | Description                  |
        |----------|------|------------------------------|
        | priority | enum | The priority of the ticket   |
    """)
    assert PITFALL in _ids(art)


def test_fires_multiple_enum_rows_two_findings():
    """Two enum rows with no values produce two findings."""
    art = _dm("""
        # Data Model

        ### Task

        | Field  | Type | Notes         |
        |--------|------|---------------|
        | status | enum | workflow step |
        | kind   | enum | task category |
    """)
    findings = _data_model_enum_no_values(art, CATALOG)
    assert len(findings) == 2
    assert all(f.pitfall_id == PITFALL for f in findings)


# ---------------------------------------------------------------------------
# Silent cases — enum field WITH value list (or no enum type)
# ---------------------------------------------------------------------------


def test_silent_enum_with_slash_separators():
    """Enum cell with '/' separated values is silent."""
    art = _dm("""
        # Data Model

        ### Order

        | Field  | Type | Notes                        |
        |--------|------|------------------------------|
        | status | enum | open / in_progress / done    |
    """)
    assert PITFALL not in _ids(art)


def test_silent_enum_with_comma_separators():
    """Enum cell where Notes has comma-separated values is silent."""
    art = _dm("""
        # Data Model

        ### User

        | Field | Type | Notes                    |
        |-------|------|--------------------------|
        | role  | enum | admin, editor, viewer    |
    """)
    assert PITFALL not in _ids(art)


def test_silent_enum_values_in_parentheses():
    """Parenthetical value list in Notes cell silences the check."""
    art = _dm("""
        # Data Model

        ### Session

        | Field  | Type | Notes                          |
        |--------|------|--------------------------------|
        | state  | enum | States: (active, expired, revoked) |
    """)
    assert PITFALL not in _ids(art)


def test_silent_non_enum_type():
    """Rows with non-enum types (UUID, TEXT, INT) are silent."""
    art = _dm("""
        # Data Model

        ### Product

        | Field      | Type      | Notes       |
        |------------|-----------|-------------|
        | id         | UUID      | Primary key |
        | name       | TEXT      | Display name|
        | price      | DECIMAL   | In USD      |
        | created_at | TIMESTAMP | Audit       |
    """)
    assert PITFALL not in _ids(art)


def test_silent_fenced_block():
    """Enum row inside a fenced code block is not flagged."""
    art = _dm("""
        # Data Model

        ### Example

        ```markdown
        | status | enum | Current state |
        ```
    """)
    assert PITFALL not in _ids(art)


def test_silent_separator_row_skipped():
    """Table separator row (|---|---|) is never flagged even if it somehow matched."""
    art = _dm("""
        # Data Model

        ### Ticket

        | Field  | Type | Notes |
        |--------|------|-------|
        | status | text | ok    |
    """)
    assert PITFALL not in _ids(art)
