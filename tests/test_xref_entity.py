"""Tests for XREF-ENTITY-NO-TASK false-positive fixes (issue #44).

Two independent improvements:
1. _entities() filters structural sub-section headings (Validation Rules,
   State Transitions, Relationships, etc.) that are not entity names.
2. The task-match uses word-boundary regex so short names like "User" do
   not match "user story", while still clearing "user" in "create user".
"""

from __future__ import annotations

import pytest

from sddgrade.adapters.base import parse_sections
from sddgrade.catalog import load_catalog
from sddgrade.engine.lint import _cross_artifact, _entities
from sddgrade.model import Artifact, ArtifactType


def _data_model(text: str) -> Artifact:
    return Artifact(
        path="data-model.md",
        type=ArtifactType.DATA_MODEL,
        feature_id="f1",
        raw=text,
        sections=parse_sections(text),
    )


def _tasks(text: str) -> Artifact:
    return Artifact(
        path="tasks.md",
        type=ArtifactType.TASKS,
        feature_id="f1",
        raw=text,
        sections=parse_sections(text),
    )


# ------------------------------------------------------------------ _entities()


def test_structural_headings_excluded():
    """Headings like Validation Rules and State Transitions must not be entities."""
    dm = _data_model(
        "# Data Model\n\n"
        "## Entities\n\n"
        "### User\n\n"
        "#### Attributes\n\n"
        "#### Validation Rules\n\n"
        "#### State Transitions\n\n"
        "### Order\n\n"
        "#### Indexes\n\n"
        "## Relationships\n\n"
        "### User-Order\n\n"
    )
    entities = _entities(dm)
    assert "User" in entities
    assert "Order" in entities
    # structural sub-sections must be excluded
    assert "Attributes" not in entities
    assert "Validation Rules" not in entities
    assert "State Transitions" not in entities
    assert "Indexes" not in entities
    # "Relationships" is at level 2 so it was already excluded; "User-Order"
    # would be inside Relationships, but with the denylist it doesn't matter
    # either way since it's a join-table label — we accept it in this case
    # as long as the structural terms are filtered.


def test_genuine_entities_returned():
    """Real entity names at level 3 must be returned."""
    dm = _data_model(
        "# Data Model\n\n"
        "## Entities\n\n"
        "### Product\n\n"
        "### Invoice\n\n"
        "### LineItem\n\n"
    )
    assert _entities(dm) == ["Product", "Invoice", "LineItem"]


def test_empty_data_model_returns_no_entities():
    dm = _data_model("# Data Model\n\nNo headings here.\n")
    assert _entities(dm) == []


def test_denylist_is_case_insensitive():
    """Denylist matching must be case-insensitive."""
    dm = _data_model(
        "# Data Model\n\n"
        "### VALIDATION RULES\n\n"
        "### State Transitions\n\n"
        "### Properties\n\n"
        "### RealEntity\n\n"
    )
    entities = _entities(dm)
    assert "RealEntity" in entities
    assert not any(
        e.lower() in {"validation rules", "state transitions", "properties"}
        for e in entities
    )


# -------------------------------------------------------- word-boundary matching


def test_entity_embedded_in_compound_word_not_cleared():
    """'User' embedded in 'createuser' must NOT clear the entity — word boundary required.

    The old substring check would clear 'User' whenever 'user' appeared anywhere,
    including as part of a compound slug like 'createuser_migration'.
    """
    dm = _data_model("# Data Model\n\n### User\n\n")
    tasks_art = _tasks(
        "# Tasks\n\n"
        "- [ ] createuser_migration script\n"
        "- [ ] setup superuser credentials\n"
    )
    catalog = load_catalog()
    findings = _cross_artifact([dm, tasks_art], catalog)
    entity_findings = [f for f in findings if f.pitfall_id == "XREF-ENTITY-NO-TASK"]
    # "createuser" and "superuser" must NOT satisfy the "User" entity requirement
    assert any("User" in f.message for f in entity_findings), (
        "Expected XREF-ENTITY-NO-TASK for 'User' when only embedded 'user' appears in tasks"
    )


def test_entity_cleared_by_word_boundary_match():
    """'User' IS cleared when tasks.md contains a standalone 'user' word."""
    dm = _data_model("# Data Model\n\n### User\n\n")
    tasks_art = _tasks(
        "# Tasks\n\n"
        "- [ ] Create user table\n"
        "- [ ] Implement user CRUD\n"
    )
    catalog = load_catalog()
    findings = _cross_artifact([dm, tasks_art], catalog)
    entity_findings = [f for f in findings if f.pitfall_id == "XREF-ENTITY-NO-TASK"]
    assert not any("User" in f.message for f in entity_findings), (
        "Expected no XREF-ENTITY-NO-TASK for 'User' when 'create user' is in tasks"
    )


def test_untasked_entity_still_flagged():
    """An entity that genuinely has no task must still be caught."""
    dm = _data_model(
        "# Data Model\n\n"
        "### Invoice\n\n"
        "### Payment\n\n"
    )
    tasks_art = _tasks(
        "# Tasks\n\n"
        "- [ ] Implement invoice generation\n"
    )
    catalog = load_catalog()
    findings = _cross_artifact([dm, tasks_art], catalog)
    entity_findings = [f for f in findings if f.pitfall_id == "XREF-ENTITY-NO-TASK"]
    assert any("Payment" in f.message for f in entity_findings)
    assert not any("Invoice" in f.message for f in entity_findings)
