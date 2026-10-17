"""Tests for DATA-MODEL-NO-FK-CONSTRAINT pitfall.

Fires when a data-model entity contains FK-style field patterns (_id suffix, FK keyword,
or 'foreign key' vocabulary) but the entity body has no referential-integrity constraint
vocabulary (ON DELETE, CASCADE, RESTRICT, SET NULL, NO ACTION, CONSTRAINT fk_, REFERENCES).

Sources: MAQA data-integrity; ISO/IEC/IEEE 29148:2018 §5.2.5(a); Canon Volere; Kiro.
"""
from __future__ import annotations

import textwrap

from sddgrade.adapters.base import parse_sections
from sddgrade.catalog import load_catalog
from sddgrade.engine.lint import _data_model_no_fk_constraint
from sddgrade.model import Artifact, ArtifactType

CATALOG = load_catalog()
PITFALL = "DATA-MODEL-NO-FK-CONSTRAINT"


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
    return [f.pitfall_id for f in _data_model_no_fk_constraint(art, CATALOG)]


# ---------------------------------------------------------------------------
# Firing cases — entity has FK field(s) but no constraint vocabulary
# ---------------------------------------------------------------------------


def test_fires_user_id_no_constraint():
    """Entity with user_id field but no ON DELETE / REFERENCES / CONSTRAINT."""
    art = _dm("""
        # Data Model

        ## Entities

        ### Order

        | Field      | Type      | Notes        |
        |------------|-----------|--------------|
        | id         | UUID      | Primary key  |
        | user_id    | UUID      | FK to User   |
        | status     | enum      | open/closed  |
        | created_at | timestamp | Audit        |
    """)
    assert PITFALL in _ids(art)


def test_fires_fk_keyword_no_constraint():
    """Entity line has 'FK' abbreviation but no constraint vocabulary."""
    art = _dm("""
        # Data Model

        ### Invoice

        - id: UUID (PK)
        - customer_id: UUID (FK)
        - amount: DECIMAL
        - created_at: TIMESTAMP
    """)
    assert PITFALL in _ids(art)


def test_fires_bare_id_suffix_no_fk_annotation():
    """Entity has _id column with no FK label and no constraint vocabulary."""
    art = _dm("""
        # Data Model

        ### Comment

        Fields:
        - id: UUID primary key
        - post_id: UUID
        - body: TEXT
        - created_at: TIMESTAMP
    """)
    assert PITFALL in _ids(art)


def test_fires_multiple_fk_fields_no_constraint():
    """Entity with multiple _id FK fields but zero constraint vocabulary."""
    art = _dm("""
        # Data Model

        ### Enrollment

        | Field      | Type | Notes         |
        |------------|------|---------------|
        | id         | UUID | PK            |
        | student_id | UUID | FK to Student |
        | course_id  | UUID | FK to Course  |
        | enrolled_at | TIMESTAMP |         |
    """)
    assert PITFALL in _ids(art)


def test_fires_fk_comment_note_only():
    """Entity has 'FK →' notation in Notes column but no real constraint vocabulary."""
    art = _dm("""
        # Data Model

        ### Payment

        | Field      | Type      | Notes         |
        |------------|-----------|---------------|
        | id         | UUID      | PK            |
        | account_id | UUID      | FK → Account  |
        | amount     | DECIMAL   |               |
        | paid_at    | TIMESTAMP |               |
    """)
    assert PITFALL in _ids(art)


# ---------------------------------------------------------------------------
# Silent cases — entity properly specifies constraint behaviour
# ---------------------------------------------------------------------------


def test_silent_on_delete_cascade():
    """Entity specifies ON DELETE CASCADE — fully constrained."""
    art = _dm("""
        # Data Model

        ### Order

        | Field      | Type      | Notes                                    |
        |------------|-----------|------------------------------------------|
        | id         | UUID      | PK                                       |
        | user_id    | UUID      | REFERENCES user(id) ON DELETE CASCADE    |
        | created_at | TIMESTAMP | Audit                                    |
    """)
    assert PITFALL not in _ids(art)


def test_silent_on_delete_restrict():
    """Entity uses RESTRICT — constraint is declared."""
    art = _dm("""
        # Data Model

        ### LineItem

        - id: UUID (PK)
        - order_id: UUID REFERENCES order(id) ON DELETE RESTRICT
        - product_id: UUID REFERENCES product(id) ON DELETE RESTRICT
        - quantity: INT
    """)
    assert PITFALL not in _ids(art)


def test_silent_constraint_keyword():
    """Entity uses CONSTRAINT fk_ syntax."""
    art = _dm("""
        # Data Model

        ### Post

        Fields:
        - id UUID PRIMARY KEY
        - author_id UUID NOT NULL
        - CONSTRAINT fk_post_author FOREIGN KEY (author_id) REFERENCES user(id)
        - created_at TIMESTAMP
    """)
    assert PITFALL not in _ids(art)


def test_silent_references_in_constraints_section():
    """Entity has a Constraints sub-section with REFERENCES vocabulary."""
    art = _dm("""
        # Data Model

        ### Subscription

        | Field       | Type      |
        |-------------|-----------|
        | id          | UUID      |
        | user_id     | UUID      |
        | plan_id     | UUID      |
        | created_at  | TIMESTAMP |

        #### Constraints

        - fk_subscription_user: user_id REFERENCES user(id) ON DELETE CASCADE
        - fk_subscription_plan: plan_id REFERENCES plan(id) ON DELETE RESTRICT
    """)
    assert PITFALL not in _ids(art)


def test_silent_set_null_strategy():
    """Entity documents SET NULL delete strategy."""
    art = _dm("""
        # Data Model

        ### Task

        - id: UUID (PK)
        - assignee_id: UUID, ON DELETE SET NULL (nullable, unassigned when user removed)
        - project_id: UUID NOT NULL REFERENCES project(id) ON DELETE CASCADE
        - created_at: TIMESTAMP
    """)
    assert PITFALL not in _ids(art)


def test_silent_foreign_key_phrase_acknowledged():
    """Entity labels the FK with 'foreign key' phrase — constraint acknowledged."""
    art = _dm("""
        # Data Model

        ### Comment

        Fields:
        - id: UUID primary key
        - post_id: UUID, foreign key to Post
        - body: TEXT
        - created_at: TIMESTAMP
    """)
    assert PITFALL not in _ids(art)


def test_silent_no_fk_fields_at_all():
    """Entity has no FK-style fields — check should not fire."""
    art = _dm("""
        # Data Model

        ### Config

        | Field | Type    | Notes       |
        |-------|---------|-------------|
        | key   | VARCHAR | Config key  |
        | value | TEXT    | Config value|
        | updated_at | TIMESTAMP | Audit |
    """)
    assert PITFALL not in _ids(art)


def test_silent_wrong_artifact_type():
    """Non-data-model artifact is always skipped."""
    raw = textwrap.dedent("""
        # Spec

        ### Order

        - order_id: UUID FK
    """).strip()
    art = Artifact(
        path="spec.md",
        type=ArtifactType.SPEC,
        feature_id="test",
        raw=raw,
        sections=parse_sections(raw),
    )
    assert PITFALL not in _ids(art)
