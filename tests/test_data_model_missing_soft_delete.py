"""Tests for DATA-MODEL-MISSING-SOFT-DELETE pitfall.

Fires when a data-model.md has ≥2 entity headings and at least one entity name
matches user-visible / transactional keywords, but the document contains no
soft-delete vocabulary anywhere in non-fenced text.

Sources: Kiro data-model production-readiness, DAMA-DMBOK, GDPR Art. 17.
"""
from __future__ import annotations

import textwrap

from sddgrade.adapters.base import parse_sections
from sddgrade.catalog import load_catalog
from sddgrade.engine.lint import _data_model_missing_soft_delete
from sddgrade.model import Artifact, ArtifactType

CATALOG = load_catalog()
PITFALL = "DATA-MODEL-MISSING-SOFT-DELETE"


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
    return [f.pitfall_id for f in _data_model_missing_soft_delete(art, CATALOG)]


# ---------------------------------------------------------------------------
# Firing cases
# ---------------------------------------------------------------------------


def test_fires_user_entity_no_soft_delete():
    """Data model with User entity but no soft-delete strategy fires."""
    art = _dm("""
        # Data Model

        ## Entities

        ### User

        | Field | Type | Notes |
        |-------|------|-------|
        | id    | UUID | PK |
        | email | string | |
        | created_at | timestamp | |

        ### Session

        | Field | Type |
        |-------|------|
        | id | UUID |
        | user_id | UUID |
    """)
    assert PITFALL in _ids(art)


def test_fires_order_entity_no_soft_delete():
    """Data model with Order entity and no soft-delete strategy fires."""
    art = _dm("""
        # Data Model

        ### Order

        | Field | Type |
        |-------|------|
        | id | UUID |
        | total | decimal |

        ### OrderItem

        | Field | Type |
        |-------|------|
        | id | UUID |
        | order_id | UUID |
    """)
    assert PITFALL in _ids(art)


def test_fires_multiple_user_visible_entities():
    """Multiple user-visible entities with no soft-delete fires once naming them."""
    art = _dm("""
        # Data Model

        ### User

        | Field | Type |
        |-------|------|
        | id | UUID |
        | name | string |

        ### Comment

        | Field | Type |
        |-------|------|
        | id | UUID |
        | body | text |
    """)
    findings = _data_model_missing_soft_delete(art, CATALOG)
    assert len(findings) == 1
    assert "User" in findings[0].message
    assert "Comment" in findings[0].message


def test_fires_product_and_invoice_entities():
    """Product and Invoice entities are user-visible; fires without soft-delete."""
    art = _dm("""
        # Data Model

        ### Product

        | Field | Type |
        |-------|------|
        | id | UUID |
        | sku | string |

        ### Invoice

        | Field | Type |
        |-------|------|
        | id | UUID |
        | amount | decimal |
    """)
    assert PITFALL in _ids(art)


def test_fires_notification_entity_no_soft_delete():
    """Notification entity is user-visible; fires without soft-delete."""
    art = _dm("""
        # Data Model

        ### Notification

        | Field | Type |
        |-------|------|
        | id | UUID |
        | message | text |

        ### NotificationChannel

        | Field | Type |
        |-------|------|
        | id | UUID |
        | type | string |
    """)
    assert PITFALL in _ids(art)


# ---------------------------------------------------------------------------
# Silent cases
# ---------------------------------------------------------------------------


def test_silent_deleted_at_present():
    """deleted_at anywhere in document silences the check."""
    art = _dm("""
        # Data Model

        ### User

        | Field | Type |
        |-------|------|
        | id | UUID |
        | email | string |
        | deleted_at | timestamp |

        ### Session

        | Field | Type |
        |-------|------|
        | id | UUID |
        | token | string |
    """)
    assert PITFALL not in _ids(art)


def test_silent_is_deleted_column():
    """is_deleted column anywhere silences the check."""
    art = _dm("""
        # Data Model

        ### Order

        | Field | Type |
        |-------|------|
        | id | UUID |
        | total | decimal |
        | is_deleted | boolean |

        ### OrderItem

        | Field | Type |
        |-------|------|
        | id | UUID |
        | quantity | int |
    """)
    assert PITFALL not in _ids(art)


def test_silent_soft_delete_mention_in_prose():
    """'soft-delete' mentioned in a notes column silences the check."""
    art = _dm("""
        # Data Model

        ### User

        | Field | Type | Notes |
        |-------|------|-------|
        | id | UUID | PK |
        | email | string | |
        | status | enum | Supports soft-delete via 'archived' status |

        ### Session

        | Field | Type |
        |-------|------|
        | id | UUID |
        | user_id | UUID |
    """)
    assert PITFALL not in _ids(art)


def test_silent_tombstone_pattern():
    """tombstone keyword silences the check."""
    art = _dm("""
        # Data Model

        ### Message

        Records use a tombstone pattern for deletion.

        | Field | Type |
        |-------|------|
        | id | UUID |
        | content | text |

        ### MessageThread

        | Field | Type |
        |-------|------|
        | id | UUID |
        | subject | string |
    """)
    assert PITFALL not in _ids(art)


def test_silent_logical_delete_mention():
    """logical-delete strategy mentioned silences the check."""
    art = _dm("""
        # Data Model

        ## Data Lifecycle

        All user records use logical-delete with a deleted_flag column.

        ### Account

        | Field | Type |
        |-------|------|
        | id | UUID |
        | email | string |

        ### Profile

        | Field | Type |
        |-------|------|
        | id | UUID |
        | display_name | string |
    """)
    assert PITFALL not in _ids(art)


def test_silent_archived_at_column():
    """archived_at column silences the check."""
    art = _dm("""
        # Data Model

        ### Post

        | Field | Type |
        |-------|------|
        | id | UUID |
        | title | string |
        | archived_at | timestamp |

        ### Tag

        | Field | Type |
        |-------|------|
        | id | UUID |
        | name | string |
    """)
    assert PITFALL not in _ids(art)


def test_silent_only_technical_entities():
    """Data model with only technical (non-user-visible) entity names does not fire."""
    art = _dm("""
        # Data Model

        ### MigrationHistory

        | Field | Type |
        |-------|------|
        | id | int |
        | applied_at | timestamp |

        ### SchemaVersion

        | Field | Type |
        |-------|------|
        | id | int |
        | checksum | string |
    """)
    assert PITFALL not in _ids(art)


def test_silent_fewer_than_two_entities():
    """Guard requires ≥2 entity headings; single entity is silent."""
    art = _dm("""
        # Data Model

        ### User

        | Field | Type |
        |-------|------|
        | id | UUID |
        | email | string |
    """)
    assert PITFALL not in _ids(art)


def test_silent_non_data_model_artifact():
    """Pitfall only applies to data-model artifacts."""
    art = _spec("""
        # Spec

        ### UserSection

        - id: UUID
        - email: string
    """)
    assert PITFALL not in _ids(art)


def test_silent_status_deleted_enum_value():
    """A status column with a 'deleted' enum value silences the check."""
    art = _dm("""
        # Data Model

        ### Account

        | Field | Type | Values |
        |-------|------|--------|
        | id | UUID | |
        | status | enum | active, suspended, deleted |

        ### Profile

        | Field | Type |
        |-------|------|
        | id | UUID |
        | bio | text |
    """)
    assert PITFALL not in _ids(art)
