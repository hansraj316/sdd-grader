"""Tests for DATA-MODEL-ENTITY-NO-INDEX pitfall.

Fires when a data-model entity contains foreign-key fields (FK/foreign key/references
vocabulary, or *_id-suffixed field names) but its body section has no index declaration.

Sources: Amazon Kiro production-readiness; ISO 25010 §4.2.1.1 Time Behaviour.
"""
from __future__ import annotations

import textwrap

from sddgrade.adapters.base import parse_sections
from sddgrade.catalog import load_catalog
from sddgrade.engine.lint import _data_model_entity_no_index
from sddgrade.model import Artifact, ArtifactType

CATALOG = load_catalog()
PITFALL = "DATA-MODEL-ENTITY-NO-INDEX"


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
    return [f.pitfall_id for f in _data_model_entity_no_index(art, CATALOG)]


# ---------------------------------------------------------------------------
# Firing cases — entity has FK field(s) but no index
# ---------------------------------------------------------------------------


def test_fires_explicit_fk_keyword_no_index():
    """Entity uses 'FK' keyword but has no index mention."""
    art = _dm("""
        # Data Model

        ## Entities

        ### Order

        | Field     | Type    | Notes           |
        |-----------|---------|-----------------|
        | id        | UUID    | Primary key     |
        | user_id   | UUID    | FK → User       |
        | status    | enum    | pending/shipped |
        | created_at | timestamp | Audit        |
    """)
    assert PITFALL in _ids(art)


def test_fires_foreign_key_phrase_no_index():
    """Entity body uses 'foreign key' phrase but no index."""
    art = _dm("""
        # Data Model

        ### Invoice

        - id: UUID (PK)
        - order_id: integer — foreign key to Order table
        - amount: decimal
        - updated_at: timestamp
    """)
    assert PITFALL in _ids(art)


def test_fires_references_keyword_no_index():
    """Entity body uses 'references' vocabulary, no index."""
    art = _dm("""
        # Data Model

        ### Payment

        | Field       | Type    | Notes                     |
        |-------------|---------|---------------------------|
        | id          | UUID    | Primary key               |
        | customer_id | UUID    | references Customer entity |
        | amount      | decimal |                           |
        | created_at  | timestamp |                         |
    """)
    assert PITFALL in _ids(art)


def test_fires_implicit_id_suffix_no_index():
    """Entity has *_id field (implicit FK) but no index declaration."""
    art = _dm("""
        # Data Model

        ### LineItem

        | Field      | Type    | Notes       |
        |------------|---------|-------------|
        | id         | UUID    | PK          |
        | product_id | UUID    | FK product  |
        | quantity   | integer |             |
    """)
    assert PITFALL in _ids(art)


def test_fires_multiple_entities_no_index():
    """Two FK-bearing entities both lack index — fires naming both."""
    art = _dm("""
        # Data Model

        ### Order

        | Field   | Type | Notes |
        |---------|------|-------|
        | id      | UUID | PK    |
        | user_id | UUID | FK    |

        ### Payment

        | Field    | Type    | Notes |
        |----------|---------|-------|
        | id       | UUID    | PK    |
        | order_id | UUID    | FK    |
    """)
    ids = _ids(art)
    assert PITFALL in ids
    findings = _data_model_entity_no_index(art, CATALOG)
    assert "Order" in findings[0].message
    assert "Payment" in findings[0].message


def test_fires_foreign_key_underscore_no_index():
    """Entity uses 'foreign_key' variant (underscore) with no index."""
    art = _dm("""
        # Data Model

        ### Subscription

        - id: UUID (PK)
        - plan_id: UUID — foreign_key
        - status: string
    """)
    assert PITFALL in _ids(art)


# ---------------------------------------------------------------------------
# Silent cases — entity has index, or no FK fields
# ---------------------------------------------------------------------------


def test_silent_no_fk_fields():
    """Entity has no FK fields at all — should not fire."""
    art = _dm("""
        # Data Model

        ### User

        | Field    | Type   | Notes       |
        |----------|--------|-------------|
        | id       | UUID   | Primary key |
        | email    | string | Unique      |
        | username | string |             |
        | created_at | timestamp | Audit  |
    """)
    assert PITFALL not in _ids(art)


def test_silent_fk_with_index_keyword():
    """Entity has FK and declares an index — silent."""
    art = _dm("""
        # Data Model

        ### Order

        | Field     | Type    | Notes       |
        |-----------|---------|-------------|
        | id        | UUID    | PK          |
        | user_id   | UUID    | FK → User   |
        | status    | enum    |             |

        #### Indexes

        - idx_orders_user_id ON (user_id)
    """)
    assert PITFALL not in _ids(art)


def test_silent_fk_with_idx_prefix():
    """Entity body mentions idx_ prefix — silences the check."""
    art = _dm("""
        # Data Model

        ### Payment

        - id: UUID (PK)
        - order_id: UUID (FK)
        - idx_payments_order_id ON (order_id)
        - amount: decimal
    """)
    assert PITFALL not in _ids(art)


def test_silent_fk_with_btree_index():
    """Entity mentions btree index — silences."""
    art = _dm("""
        # Data Model

        ### Shipment

        - id: UUID (PK)
        - carrier_id: UUID (FK → Carrier)
        - btree index on carrier_id
    """)
    assert PITFALL not in _ids(art)


def test_silent_no_entities():
    """Data model with no entity headings — no findings."""
    art = _dm("""
        # Data Model

        This document describes the data model.

        Some tables will be defined later.
    """)
    assert PITFALL not in _ids(art)


def test_silent_spec_artifact_ignored():
    """A SPEC artifact is not a data-model — check returns nothing."""
    raw = textwrap.dedent("""
        # Spec

        ### Order

        - user_id: UUID (FK)
    """).strip()
    art = Artifact(
        path="spec.md",
        type=ArtifactType.SPEC,
        feature_id="test",
        raw=raw,
        sections=parse_sections(raw),
    )
    assert PITFALL not in _ids(art)


def test_silent_fk_with_indexed_on():
    """'indexed on' phrase silences the check."""
    art = _dm("""
        # Data Model

        ### Comment

        | Field   | Type | Notes                   |
        |---------|------|-------------------------|
        | id      | UUID | PK                      |
        | post_id | UUID | FK → Post, indexed on post_id |
    """)
    assert PITFALL not in _ids(art)


def test_silent_fk_mixed_one_has_index():
    """One entity has FK+index, the other has FK without index — only flags latter."""
    art = _dm("""
        # Data Model

        ### Tag

        | Field   | Type | Notes              |
        |---------|------|--------------------|
        | id      | UUID | PK                 |
        | post_id | UUID | FK, create index   |

        ### Vote

        | Field   | Type | Notes |
        |---------|------|-------|
        | id      | UUID | PK    |
        | user_id | UUID | FK    |
    """)
    ids = _ids(art)
    assert PITFALL in ids
    findings = _data_model_entity_no_index(art, CATALOG)
    assert "Vote" in findings[0].message
    assert "Tag" not in findings[0].message
