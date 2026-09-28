"""Tests for DATA-MODEL-ENTITY-NO-TIMESTAMPS pitfall.

Fires when a data-model.md entity (level-3+ heading, not a structural sub-heading)
has no audit-timestamp vocabulary (created_at/updated_at and variants) in its body.

Sources: ISO 27001 A.12.4, GDPR Article 30, Kiro production-readiness, DAMA-DMBOK.
"""
from __future__ import annotations

import textwrap

from sddgrade.adapters.base import parse_sections
from sddgrade.catalog import load_catalog
from sddgrade.engine.lint import _data_model_entity_no_timestamps
from sddgrade.model import Artifact, ArtifactType

CATALOG = load_catalog()
PITFALL = "DATA-MODEL-ENTITY-NO-TIMESTAMPS"


def _dm(raw: str) -> Artifact:
    raw = textwrap.dedent(raw).strip()
    return Artifact(
        path="data-model.md",
        type=ArtifactType.DATA_MODEL,
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
    return [f.pitfall_id for f in _data_model_entity_no_timestamps(art, CATALOG)]


# ---------------------------------------------------------------------------
# Firing cases — entity bodies with no audit-timestamp vocabulary
# ---------------------------------------------------------------------------


def test_fires_entity_no_timestamps():
    """Entity with only business fields and no created_at/updated_at."""
    art = _dm("""
        # Data Model

        ## Entities

        ### Order

        | Field | Type | Notes |
        |-------|------|-------|
        | id    | UUID | Primary key |
        | amount | decimal | Order total |
        | status | enum | pending/shipped |
    """)
    assert PITFALL in _ids(art)


def test_fires_multiple_entities_all_missing_timestamps():
    """Both entities lack audit timestamp fields — fires once naming both."""
    art = _dm("""
        # Data Model

        ## Entities

        ### Invoice

        | Field | Type |
        |-------|------|
        | id | UUID |
        | total | decimal |

        ### Customer

        | Field | Type |
        |-------|------|
        | id | UUID |
        | name | string |
    """)
    findings = _data_model_entity_no_timestamps(art, CATALOG)
    assert len(findings) == 1
    assert "Invoice" in findings[0].message
    assert "Customer" in findings[0].message


def test_fires_entity_with_due_date_but_no_audit_timestamp():
    """due_date is a business field, not an audit timestamp."""
    art = _dm("""
        # Data Model

        ### Task

        | Field | Type |
        |-------|------|
        | id | string |
        | due_date | date |
        | priority | int |
    """)
    assert PITFALL in _ids(art)


def test_fires_entity_with_date_type_but_no_audit_column():
    """'date' as a column type without created_at/updated_at still fires."""
    art = _dm("""
        # Data Model

        ### Report

        | Field | Type | Notes |
        |-------|------|-------|
        | id | UUID | PK |
        | title | string | Report title |
        | publish_date | date | When published |
    """)
    assert PITFALL in _ids(art)


def test_fires_partial_one_missing_timestamps():
    """One entity has timestamps, one does not — finding names only the missing one."""
    art = _dm("""
        # Data Model

        ### User

        | Field | Type |
        |-------|------|
        | id | UUID |
        | name | string |
        | created_at | timestamp |
        | updated_at | timestamp |

        ### Session

        | Field | Type |
        |-------|------|
        | id | UUID |
        | token | string |
    """)
    findings = _data_model_entity_no_timestamps(art, CATALOG)
    assert len(findings) == 1
    assert "Session" in findings[0].message
    assert "User" not in findings[0].message


# ---------------------------------------------------------------------------
# Silent cases — various forms of audit-timestamp vocabulary present
# ---------------------------------------------------------------------------


def test_silent_created_at():
    """Entity with created_at is silent."""
    art = _dm("""
        # Data Model

        ### Payment

        | Field | Type |
        |-------|------|
        | id | UUID |
        | amount | decimal |
        | created_at | timestamp |
    """)
    assert PITFALL not in _ids(art)


def test_silent_updated_at():
    """Entity with updated_at is silent."""
    art = _dm("""
        # Data Model

        ### Comment

        | Field | Type |
        |-------|------|
        | id | UUID |
        | body | text |
        | updated_at | timestamp |
    """)
    assert PITFALL not in _ids(art)


def test_silent_created_on_variant():
    """'created_on' variant counts as an audit timestamp."""
    art = _dm("""
        # Data Model

        ### Subscription

        | Field | Type |
        |-------|------|
        | id | int |
        | plan | string |
        | created_on | date |
        | updated_on | date |
    """)
    assert PITFALL not in _ids(art)


def test_silent_camel_case_createdAt():
    """camelCase 'createdAt' is silenced."""
    art = _dm("""
        # Data Model

        ### Event

        | Field | Type |
        |-------|------|
        | id | UUID |
        | name | string |
        | createdAt | DateTime |
        | updatedAt | DateTime |
    """)
    assert PITFALL not in _ids(art)


def test_silent_last_modified():
    """'last_modified' counts as an audit timestamp."""
    art = _dm("""
        # Data Model

        ### Document

        | Field | Type |
        |-------|------|
        | id | UUID |
        | content | text |
        | last_modified | timestamp |
    """)
    assert PITFALL not in _ids(art)


def test_silent_modification_date():
    """'modification_date' counts as an audit timestamp."""
    art = _dm("""
        # Data Model

        ### Record

        | Field | Type |
        |-------|------|
        | id | int |
        | value | float |
        | creation_date | datetime |
        | modification_date | datetime |
    """)
    assert PITFALL not in _ids(art)


def test_silent_structural_subheading_skipped():
    """'Indexes' sub-heading is structural and not treated as an entity."""
    art = _dm("""
        # Data Model

        ### User

        | Field | Type |
        |-------|------|
        | id | UUID |
        | email | string |
        | created_at | timestamp |

        #### Indexes

        - idx_user_email on email
    """)
    assert PITFALL not in _ids(art)


def test_silent_no_entities_in_data_model():
    """Data model with no level-3+ headings is silent."""
    art = _dm("""
        # Data Model

        ## Overview

        No new entities are introduced by this feature.
    """)
    assert PITFALL not in _ids(art)


def test_silent_non_data_model_artifact():
    """Pitfall only applies to data-model artifacts, not spec."""
    art = _spec("""
        # Spec

        ### SomeSection

        - id: UUID
        - amount: decimal
    """)
    assert PITFALL not in _ids(art)


def test_silent_inserted_at_variant():
    """'inserted_at' (Ecto/Elixir convention) counts as an audit timestamp."""
    art = _dm("""
        # Data Model

        ### Message

        | Field | Type |
        |-------|------|
        | id | UUID |
        | content | text |
        | inserted_at | naive_datetime |
        | updated_at | naive_datetime |
    """)
    assert PITFALL not in _ids(art)
