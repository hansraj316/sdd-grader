"""Tests for DATA-MODEL-ENTITY-NO-PK pitfall.

Fires when a data-model.md entity (level-3+ heading, not a structural sub-heading)
has no PK vocabulary (id/ID/primary key/PK/uuid/UUID/unique identifier/surrogate key)
in its body section.

Sources: ISO/IEC 11179, relational data-modeling best practices, Spec-Kit data-model
template.
"""
from __future__ import annotations

import textwrap

from sddgrade.adapters.base import parse_sections
from sddgrade.catalog import load_catalog
from sddgrade.engine.lint import _data_model_entity_no_pk
from sddgrade.model import Artifact, ArtifactType

CATALOG = load_catalog()
PITFALL = "DATA-MODEL-ENTITY-NO-PK"


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
    return [f.pitfall_id for f in _data_model_entity_no_pk(art, CATALOG)]


# ---------------------------------------------------------------------------
# Firing cases — entity bodies with no PK vocabulary
# ---------------------------------------------------------------------------


def test_fires_entity_no_pk_field():
    """Entity with only name/status fields and no id/PK."""
    art = _dm("""
        # Data Model

        ## Entities

        ### Order

        | Field | Type | Notes |
        |-------|------|-------|
        | name  | string | Order name |
        | status | enum | active/inactive |
    """)
    assert PITFALL in _ids(art)


def test_fires_multiple_entities_all_missing_pk():
    """Both entities lack a PK field — fires once with both names."""
    art = _dm("""
        # Data Model

        ## Entities

        ### Invoice

        | Field | Type |
        |-------|------|
        | amount | decimal |
        | currency | string |

        ### LineItem

        | Field | Type |
        |-------|------|
        | description | string |
        | quantity | int |
    """)
    findings = _data_model_entity_no_pk(art, CATALOG)
    assert len(findings) == 1
    assert PITFALL in findings[0].pitfall_id
    assert "Invoice" in findings[0].message or "LineItem" in findings[0].message


def test_fires_one_of_two_entities_missing_pk():
    """One entity has id, the other does not — fires for the missing one."""
    art = _dm("""
        # Data Model

        ### User

        | Field | Type | Notes |
        |-------|------|-------|
        | id | UUID | Primary key |
        | email | string | Unique email |

        ### Session

        | Field | Type | Notes |
        |-------|------|-------|
        | token | string | Auth token |
        | expiry | datetime | Expiration |
    """)
    findings = _data_model_entity_no_pk(art, CATALOG)
    assert len(findings) == 1
    assert "Session" in findings[0].message


def test_fires_entity_body_only_prose_no_pk():
    """Entity body is prose with no id/PK mention."""
    art = _dm("""
        # Data Model

        ### Product

        Describes a product available for purchase.
        Has a name, description, and price.
    """)
    assert PITFALL in _ids(art)


def test_fires_entity_capitalized_fields_no_pk():
    """Entity fields are named Name/Status — none are PK-related."""
    art = _dm("""
        # Data Model

        ### Category

        | Field | Type |
        |-------|------|
        | Name | string |
        | ParentCategory | string |
    """)
    assert PITFALL in _ids(art)


# ---------------------------------------------------------------------------
# Silent cases — entity bodies with PK vocabulary
# ---------------------------------------------------------------------------


def test_silent_entity_with_id_field():
    """Entity has 'id' field — silent."""
    art = _dm("""
        # Data Model

        ### Task

        | Field | Type | Notes |
        |-------|------|-------|
        | id | string | Stable identifier |
        | title | string | Human-readable |
    """)
    assert _ids(art) == []


def test_silent_entity_with_uuid_field():
    """Entity has 'uuid' field — silent."""
    art = _dm("""
        # Data Model

        ### Payment

        | Field | Type | Notes |
        |-------|------|-------|
        | uuid | UUID | Globally unique payment ID |
        | amount | decimal | Payment amount |
    """)
    assert _ids(art) == []


def test_silent_entity_with_primary_key_note():
    """Entity body mentions 'primary key' in prose — silent."""
    art = _dm("""
        # Data Model

        ### Order

        | Field | Type | Notes |
        |-------|------|-------|
        | order_id | bigint | Primary key, auto-increment |
        | total | decimal | Order total |
    """)
    assert _ids(art) == []


def test_silent_entity_with_pk_abbreviation():
    """Entity body has 'PK' annotation — silent."""
    art = _dm("""
        # Data Model

        ### Customer

        | customer_id | int | PK |
        | name | string | Full name |
    """)
    assert _ids(art) == []


def test_silent_entity_with_surrogate_key():
    """Entity body mentions 'surrogate key' — silent."""
    art = _dm("""
        # Data Model

        ### Event

        surrogate key: event_id (auto-generated UUID)

        | Field | Type |
        |-------|------|
        | event_id | UUID |
        | event_type | string |
    """)
    assert _ids(art) == []


def test_silent_entity_with_unique_identifier():
    """Entity body mentions 'unique identifier' — silent."""
    art = _dm("""
        # Data Model

        ### Subscription

        Each subscription has a unique identifier assigned at creation.

        | Field | Type |
        |-------|------|
        | sub_code | string |
    """)
    assert _ids(art) == []


def test_silent_no_entities():
    """Data-model with no entities (level-3+ headings) — silent."""
    art = _dm("""
        # Data Model

        ## Overview

        No new entities are introduced by this feature.

        ## Relationships

        Reuses existing User and Task models.
    """)
    assert _ids(art) == []


def test_silent_structural_subheading_ignored():
    """Level-3 headings that are structural sub-headings (Attributes, Indexes) are ignored."""
    art = _dm("""
        # Data Model

        ### Widget

        | id | UUID | Primary key |

        #### Attributes

        name, description, price

        #### Indexes

        (id), (name)
    """)
    assert _ids(art) == []


def test_silent_spec_artifact_not_checked():
    """Spec artifact — check does not apply."""
    art = _spec("""
        # Spec

        ### SomeSection

        No primary key here.
    """)
    assert _ids(art) == []
