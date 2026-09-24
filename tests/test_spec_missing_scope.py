"""Tests for SPEC-MISSING-SCOPE pitfall.

Fires when a spec.md has ≥3 non-fenced FR-/NFR- requirement lines but no
section heading that matches a scope declaration (Scope, System Scope, Project
Scope, Product Scope, Application Scope, Solution Scope, Feature Scope).

Sources: ISO/IEC/IEEE 29148:2018 §5.2.1; Canon Volere §2; Amazon Kiro spec template.
"""
from __future__ import annotations

import textwrap

from sddgrade.adapters.base import parse_sections
from sddgrade.catalog import load_catalog
from sddgrade.engine.lint import _spec_missing_scope
from sddgrade.model import Artifact, ArtifactType

CATALOG = load_catalog()
PITFALL = "SPEC-MISSING-SCOPE"


def _spec(raw: str) -> Artifact:
    raw = textwrap.dedent(raw).strip()
    return Artifact(
        path="spec.md",
        type=ArtifactType.SPEC,
        feature_id="test",
        raw=raw,
        sections=parse_sections(raw),
    )


def _plan(raw: str) -> Artifact:
    raw = textwrap.dedent(raw).strip()
    return Artifact(
        path="plan.md",
        type=ArtifactType.PLAN,
        feature_id="test",
        raw=raw,
        sections=parse_sections(raw),
    )


def _tasks(raw: str) -> Artifact:
    raw = textwrap.dedent(raw).strip()
    return Artifact(
        path="tasks.md",
        type=ArtifactType.TASKS,
        feature_id="test",
        raw=raw,
        sections=parse_sections(raw),
    )


def _ids(art: Artifact) -> list[str]:
    return [f.pitfall_id for f in _spec_missing_scope(art, CATALOG)]


# ---------------------------------------------------------------------------
# FIRE cases
# ---------------------------------------------------------------------------


def test_fires_spec_with_reqs_no_scope():
    """Spec with 3+ FR-/NFR- lines but no scope heading fires."""
    art = _spec("""
        # Feature Spec

        ## Problem Statement
        Teams need a faster way to onboard.

        ## Requirements
        FR-001: The system shall allow bulk user import.
        FR-002: The system shall validate each row.
        FR-003: The system shall report import errors.
    """)
    assert PITFALL in _ids(art)


def test_fires_only_out_of_scope_heading():
    """'Out of Scope' heading does not satisfy the Scope check."""
    art = _spec("""
        # Feature Spec

        ## Out of Scope
        PDF export is excluded.

        ## Requirements
        FR-001: The system shall export tasks.
        FR-002: The system shall filter by status.
        NFR-001: The system shall complete export in under 2 s.
    """)
    assert PITFALL in _ids(art)


def test_fires_out_of_scope_variant_non_goals():
    """'Non-goals' heading is not a scope section — fires."""
    art = _spec("""
        # Feature Spec

        ## Non-goals
        Real-time streaming is not in scope.

        ## Requirements
        FR-001: The system shall parse CSV.
        FR-002: The system shall validate headers.
        FR-003: The system shall emit errors.
    """)
    assert PITFALL in _ids(art)


def test_fires_scope_word_in_prose_not_heading():
    """'scope' appearing only in prose, not as a heading, fires."""
    art = _spec("""
        # Feature Spec
        This spec covers the scope of the export feature.

        ## Requirements
        FR-001: The system shall export.
        FR-002: The system shall filter.
        FR-003: The system shall validate.
    """)
    assert PITFALL in _ids(art)


# ---------------------------------------------------------------------------
# SILENT cases
# ---------------------------------------------------------------------------


def test_silent_scope_heading_present():
    """Spec with a '## Scope' heading is silent."""
    art = _spec("""
        # Feature Spec

        ## Scope
        This spec covers CSV export for the web app.

        ## Requirements
        FR-001: The system shall export tasks to CSV.
        FR-002: The system shall filter by status.
        FR-003: The system shall escape field values.
    """)
    assert PITFALL not in _ids(art)


def test_silent_system_scope_heading():
    """'## System Scope' heading satisfies the check."""
    art = _spec("""
        # Feature Spec

        ## System Scope
        Covers authentication module only.

        ## Requirements
        FR-001: The system shall authenticate users.
        FR-002: The system shall issue JWT tokens.
        FR-003: The system shall revoke sessions.
    """)
    assert PITFALL not in _ids(art)


def test_silent_project_scope_heading():
    """'## Project Scope' heading is accepted."""
    art = _spec("""
        # Feature Spec

        ## Project Scope
        Phase 1 only.

        ## Requirements
        FR-001: The system shall do X.
        FR-002: The system shall do Y.
        NFR-001: The system shall respond within 200 ms.
    """)
    assert PITFALL not in _ids(art)


def test_silent_product_scope_heading():
    """'## Product Scope' heading satisfies the check."""
    art = _spec("""
        # Feature Spec

        ## Product Scope
        Applies to the mobile app.

        ## Requirements
        FR-001: The system shall sync offline data.
        FR-002: The system shall show conflict banners.
        FR-003: The system shall resolve via last-write-wins.
    """)
    assert PITFALL not in _ids(art)


def test_silent_feature_scope_heading():
    """'## Feature Scope' heading satisfies the check."""
    art = _spec("""
        # Feature Spec

        ## Feature Scope
        Only the export dialog.

        ## Requirements
        FR-001: The system shall export.
        FR-002: The system shall allow format selection.
        FR-003: The system shall validate before export.
    """)
    assert PITFALL not in _ids(art)


def test_silent_fewer_than_three_reqs():
    """Guard requires ≥3 FR-/NFR- lines; fewer than 3 is silent."""
    art = _spec("""
        # Feature Spec

        ## Requirements
        FR-001: The system shall allow login.
        FR-002: The system shall allow logout.
    """)
    assert PITFALL not in _ids(art)


def test_silent_plan_artifact():
    """Plan artifacts are not checked."""
    art = _plan("""
        # Deployment Plan

        ## Deploy Steps
        FR-001: steps.
        FR-002: more steps.
        FR-003: rollback steps.
    """)
    assert PITFALL not in _ids(art)


def test_silent_tasks_artifact():
    """Tasks artifacts are not checked."""
    art = _tasks("""
        # Tasks

        ## Sprint
        FR-001 task.
        FR-002 task.
        FR-003 task.
    """)
    assert PITFALL not in _ids(art)


def test_silent_fenced_reqs_only():
    """FR-/NFR- lines inside fenced code blocks don't count toward guard."""
    art = _spec("""
        # Feature Spec

        ## Requirements
        ```
        FR-001: The system shall do X.
        FR-002: The system shall do Y.
        FR-003: The system shall do Z.
        ```
    """)
    assert PITFALL not in _ids(art)


def test_silent_scope_heading_case_insensitive():
    """'## SCOPE' (all caps) satisfies the check."""
    art = _spec("""
        # Feature Spec

        ## SCOPE
        Applies to the payments module.

        ## Requirements
        FR-001: The system shall process payments.
        FR-002: The system shall refund payments.
        NFR-001: The system shall complete payment in under 3 s.
    """)
    assert PITFALL not in _ids(art)
