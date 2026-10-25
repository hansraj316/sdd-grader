"""Unit tests for TASKS-NO-PHASE-DEPENDENCY pitfall."""

from __future__ import annotations

import textwrap

from sddgrade.adapters.base import parse_sections
from sddgrade.catalog import load_catalog
from sddgrade.engine.lint import _tasks_no_phase_dependency
from sddgrade.model import Artifact, ArtifactType

CATALOG = load_catalog()
PITFALL = "TASKS-NO-PHASE-DEPENDENCY"


def _tasks(raw: str) -> Artifact:
    raw = textwrap.dedent(raw).strip()
    return Artifact(
        path="tasks.md",
        type=ArtifactType.TASKS,
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


# ── FIRE cases ───────────────────────────────────────────────────────────────


def test_two_phases_no_dep_section_fires():
    art = _tasks("""
        ## Phase 1: Setup
        - [ ] T001 [US1] Create skeleton (1 sp)

        ## Phase 2: Implementation
        - [ ] T002 [US1] Add query helper (2 sp)
    """)
    findings = _tasks_no_phase_dependency(art, CATALOG)
    assert len(findings) == 1
    assert findings[0].pitfall_id == PITFALL
    assert findings[0].line == 1


def test_three_phases_no_dep_section_fires():
    art = _tasks("""
        ## Phase 1: Setup
        - [ ] T001 [US1] Bootstrap project (1 sp)

        ## Phase 2: Implementation
        - [ ] T002 [US1] Implement feature (3 sp)

        ## Phase 3: Hardening
        - [ ] T003 [US1] Add monitoring (2 sp)
    """)
    findings = _tasks_no_phase_dependency(art, CATALOG)
    assert len(findings) == 1
    assert findings[0].pitfall_id == PITFALL


def test_phase_headings_level4_fires():
    art = _tasks("""
        #### Phase A: Bootstrap
        - [ ] T001 [US1] Do thing (1 sp)

        #### Phase B: Ship
        - [ ] T002 [US1] Ship it (1 sp)
    """)
    findings = _tasks_no_phase_dependency(art, CATALOG)
    assert len(findings) == 1
    assert findings[0].pitfall_id == PITFALL


def test_phase_headings_mixed_levels_fires():
    art = _tasks("""
        # Phase 1: Alpha
        - [ ] T001 [US1] Alpha task (1 sp)

        ## Phase 2: Beta
        - [ ] T002 [US1] Beta task (2 sp)
    """)
    findings = _tasks_no_phase_dependency(art, CATALOG)
    assert len(findings) == 1


# ── SILENT cases ─────────────────────────────────────────────────────────────


def test_single_phase_silent():
    art = _tasks("""
        ## Phase 1: Setup
        - [ ] T001 [US1] Create skeleton (1 sp)
        - [ ] T002 [US1] Configure CI (1 sp)
    """)
    findings = _tasks_no_phase_dependency(art, CATALOG)
    assert findings == []


def test_two_phases_with_dependencies_section_silent():
    art = _tasks("""
        ## Phase 1: Setup
        - [ ] T001 [US1] Bootstrap (1 sp)

        ## Phase 2: Implementation
        - [ ] T002 [US1] Add feature (2 sp)

        ## Dependencies & Execution Order
        Phase 1 must complete before Phase 2.
    """)
    findings = _tasks_no_phase_dependency(art, CATALOG)
    assert findings == []


def test_two_phases_with_execution_order_section_silent():
    art = _tasks("""
        ## Phase 1
        - [ ] T001 [US1] Task one (1 sp)

        ## Phase 2
        - [ ] T002 [US1] Task two (1 sp)

        ## Execution Order
        Run Phase 1 before Phase 2.
    """)
    findings = _tasks_no_phase_dependency(art, CATALOG)
    assert findings == []


def test_no_phases_at_all_silent():
    art = _tasks("""
        ## Implementation Tasks
        - [ ] T001 [US1] Build API (2 sp)

        ## Test Tasks
        - [ ] T002 [US1] Write unit tests (1 sp)
    """)
    findings = _tasks_no_phase_dependency(art, CATALOG)
    assert findings == []


def test_spec_artifact_not_tasks_silent():
    art = _spec("""
        ## Phase 1: Setup
        FR-001: The system shall configure the environment.

        ## Phase 2: Deployment
        FR-002: The system shall deploy the service.
    """)
    findings = _tasks_no_phase_dependency(art, CATALOG)
    assert findings == []


def test_phase_keyword_in_fenced_block_not_counted():
    art = _tasks("""
        ## Phase 1: Real Phase
        - [ ] T001 [US1] Real task (1 sp)

        ```
        ## Phase 2: This is in a code block
        some code here
        ```
    """)
    # Only 1 real Phase heading → should not fire
    findings = _tasks_no_phase_dependency(art, CATALOG)
    assert findings == []


def test_dependencies_heading_case_insensitive_silent():
    art = _tasks("""
        ## Phase 1: Setup
        - [ ] T001 [US1] Task (1 sp)

        ## Phase 2: Run
        - [ ] T002 [US1] Other task (2 sp)

        ## DEPENDENCIES
        Phase 1 before Phase 2.
    """)
    findings = _tasks_no_phase_dependency(art, CATALOG)
    assert findings == []
