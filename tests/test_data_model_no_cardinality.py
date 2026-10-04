"""Tests for DATA-MODEL-NO-CARDINALITY pitfall.

Fires when a data-model artifact with ≥2 entity headings contains FK/relationship
vocabulary but no cardinality notation anywhere in the document.

Sources: ISO/IEC/IEEE 29148:2018 §9.5.5; IEEE 12207 data-architecture quality.
"""
from __future__ import annotations

import textwrap

from sddgrade.adapters.base import parse_sections
from sddgrade.catalog import load_catalog
from sddgrade.engine.lint import _data_model_no_cardinality
from sddgrade.model import Artifact, ArtifactType

CATALOG = load_catalog()
PITFALL = "DATA-MODEL-NO-CARDINALITY"


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
    return [f.pitfall_id for f in _data_model_no_cardinality(art, CATALOG)]


# ---------------------------------------------------------------------------
# Firing cases — FK vocabulary present but no cardinality notation
# ---------------------------------------------------------------------------


def test_fires_fk_keyword_no_cardinality():
    """Explicit FK keyword without any cardinality notation."""
    art = _dm("""
        # Data Model

        ### User

        | Field | Type | Notes |
        |-------|------|-------|
        | id    | UUID | PK    |

        ### Order

        | Field   | Type | Notes         |
        |---------|------|---------------|
        | id      | UUID | PK            |
        | user_id | UUID | FK → User     |
    """)
    assert PITFALL in _ids(art)


def test_fires_foreign_key_phrase_no_cardinality():
    """'foreign key' phrase without any cardinality notation."""
    art = _dm("""
        # Data Model

        ### Product

        - id: UUID (PK)
        - name: string

        ### OrderItem

        - id: UUID (PK)
        - order_id: integer — foreign key to Order
        - quantity: integer
    """)
    assert PITFALL in _ids(art)


def test_fires_references_no_cardinality():
    """'references' vocabulary without cardinality."""
    art = _dm("""
        # Data Model

        ### Invoice

        | id | UUID | PK |

        ### Payment

        | id         | UUID | PK                     |
        | invoice_id | UUID | references Invoice.id  |
    """)
    assert PITFALL in _ids(art)


def test_fires_has_many_no_cardinality():
    """'has many' relationship vocabulary without cardinality."""
    art = _dm("""
        # Data Model

        ### Team

        A team has many Members.

        ### Member

        | id      | UUID | PK |
        | team_id | UUID | FK |
    """)
    assert PITFALL in _ids(art)


def test_fires_belongs_to_no_cardinality():
    """'belongs to' relationship without cardinality."""
    art = _dm("""
        # Data Model

        ### Post

        - id: UUID
        - author_id: UUID — belongs to User

        ### Comment

        - id: UUID
        - post_id: UUID
    """)
    assert PITFALL in _ids(art)


def test_fires_id_suffix_field_no_cardinality():
    """_id-suffixed field without cardinality notation."""
    art = _dm("""
        # Data Model

        ### Category

        | id   | UUID | PK |
        | name | text |    |

        ### Article

        | id          | UUID | PK                |
        | category_id | UUID | FK to Category    |
        | title       | text |                   |
    """)
    assert PITFALL in _ids(art)


# ---------------------------------------------------------------------------
# Silent cases — cardinality is declared
# ---------------------------------------------------------------------------


def test_silent_with_1_to_n_notation():
    """Cardinality '1:N' present — should not fire."""
    art = _dm("""
        # Data Model

        ### User

        | id | UUID | PK |

        ### Order

        | id      | UUID | PK              |
        | user_id | UUID | FK → User (1:N) |
    """)
    assert PITFALL not in _ids(art)


def test_silent_with_one_to_many_text():
    """'one-to-many' text present — should not fire."""
    art = _dm("""
        # Data Model

        ### Team

        | id | UUID | PK |

        ### Member

        #### Relationships
        - Team → Member: one-to-many

        | id      | UUID | PK        |
        | team_id | UUID | FK → Team |
    """)
    assert PITFALL not in _ids(art)


def test_silent_with_many_to_many():
    """'many-to-many' text present — should not fire."""
    art = _dm("""
        # Data Model

        ### Student

        | id | UUID | PK |

        ### Course

        | id | UUID | PK |

        Student ↔ Course: many-to-many via Enrollment

        ### Enrollment

        | student_id | UUID | FK |
        | course_id  | UUID | FK |
    """)
    assert PITFALL not in _ids(art)


def test_silent_with_n_m_notation():
    """'N:M' notation present — should not fire."""
    art = _dm("""
        # Data Model

        ### Tag

        | id | UUID | PK |

        ### Post

        | id | UUID | PK |

        Relationship Post ↔ Tag is N:M.

        ### PostTag

        | post_id | UUID | FK |
        | tag_id  | UUID | FK |
    """)
    assert PITFALL not in _ids(art)


def test_silent_with_cardinality_word():
    """Explicit 'cardinality' keyword present — should not fire."""
    art = _dm("""
        # Data Model

        ### Department

        | id | UUID | PK |

        ### Employee

        Cardinality: one department has many employees.

        | id            | UUID | PK        |
        | department_id | UUID | FK        |
    """)
    assert PITFALL not in _ids(art)


def test_silent_no_fk_vocabulary():
    """No FK/relationship vocabulary present — guard does not trigger."""
    art = _dm("""
        # Data Model

        ### User

        | id    | UUID | PK   |
        | email | text | Unique |

        ### Session

        | id         | UUID | PK          |
        | token      | text | access token |
        | expires_at | timestamp |         |
    """)
    assert PITFALL not in _ids(art)


def test_silent_only_one_entity():
    """Only 1 entity heading — guard requires ≥2, should not fire."""
    art = _dm("""
        # Data Model

        ### Order

        | id      | UUID | PK        |
        | user_id | UUID | FK → User |
    """)
    assert PITFALL not in _ids(art)


def test_silent_non_data_model_artifact():
    """Non-data-model artifact is always skipped."""
    raw = textwrap.dedent("""
        # Spec

        ### User

        | id      | UUID | PK        |
        | user_id | UUID | FK → Org  |

        ### Org

        | id | UUID | PK |
    """).strip()
    art = Artifact(
        path="spec.md",
        type=ArtifactType.SPEC,
        feature_id="test",
        raw=raw,
        sections=parse_sections(raw),
    )
    assert PITFALL not in [f.pitfall_id for f in _data_model_no_cardinality(art, CATALOG)]


def test_silent_fk_in_fenced_block():
    """FK vocabulary inside a fenced code block should not trigger."""
    art = _dm("""
        # Data Model

        ### User

        | id | UUID | PK |

        ### Order

        | id | UUID | PK |

        ```sql
        ALTER TABLE orders ADD COLUMN user_id UUID REFERENCES users(id);
        ```
    """)
    # No FK vocab outside fence → should not fire.
    assert PITFALL not in _ids(art)
