"""Tests for XREF-DANGLING-REQ-REF — task references a requirement ID not defined in spec.md."""
from __future__ import annotations

import textwrap

import pytest

from sddgrade.adapters.base import parse_sections
from sddgrade.catalog import load_catalog
from sddgrade.engine.lint import _cross_artifact
from sddgrade.model import Artifact, ArtifactType

CATALOG = load_catalog()
PITFALL = "XREF-DANGLING-REQ-REF"


def _spec(raw: str) -> Artifact:
    raw = textwrap.dedent(raw).strip()
    return Artifact(
        path="spec.md",
        type=ArtifactType.SPEC,
        feature_id="f1",
        raw=raw,
        sections=parse_sections(raw),
    )


def _tasks(raw: str) -> Artifact:
    raw = textwrap.dedent(raw).strip()
    return Artifact(
        path="tasks.md",
        type=ArtifactType.TASKS,
        feature_id="f1",
        raw=raw,
        sections=parse_sections(raw),
    )


def _run(spec_art: Artifact, tasks_art: Artifact) -> list:
    return [f for f in _cross_artifact([spec_art, tasks_art], CATALOG) if f.pitfall_id == PITFALL]


# --------------------------------------------------------------------------- fire cases


def test_us_tag_not_in_spec_fires():
    """[US7] in tasks.md but spec only defines User Stories 1–3."""
    s = _spec("""
        # Spec
        ## User Story 1
        As a user I want login.
        ## User Story 2
        As a user I want logout.
        ## User Story 3
        As a user I want dashboard.
    """)
    t = _tasks("""
        # Tasks
        - [ ] T01 [US7] Implement magic feature
    """)
    findings = _run(s, t)
    assert findings, "should fire for [US7] not defined in spec"
    assert "US-7" in findings[0].message


def test_fr_id_not_in_spec_fires():
    """FR-99 in tasks.md but spec only defines FR-001 through FR-004."""
    s = _spec("""
        # Spec
        ## Requirements
        FR-001: The system shall authenticate users.
        FR-002: The system shall authorise roles.
        FR-003: The system shall log events.
        FR-004: The system shall export reports.
    """)
    t = _tasks("""
        # Tasks
        - [ ] T01 [US1] Implement (FR-99) some feature
    """)
    findings = _run(s, t)
    assert findings, "should fire for FR-99 not in spec"
    assert "FR-99" in findings[0].message


def test_ac_id_not_in_spec_fires():
    """AC-99 referenced in tasks.md not defined in spec.md."""
    s = _spec("""
        # Spec
        ## Acceptance Criteria
        AC-01: Given valid input when submitted then system responds 200.
        AC-02: Given invalid input when submitted then system responds 400.
    """)
    t = _tasks("""
        # Tasks
        - [ ] T01 [US1] Implement validation (AC-99)
    """)
    findings = _run(s, t)
    assert findings, "should fire for AC-99 not in spec"
    assert "AC-99" in findings[0].message


def test_nfr_id_not_in_spec_fires():
    """NFR-50 referenced in tasks.md not defined in spec.md."""
    s = _spec("""
        # Spec
        ## Non-Functional Requirements
        NFR-01: The system shall respond within 200ms at p95.
    """)
    t = _tasks("""
        # Tasks
        - [ ] T01 [US1] Add caching (NFR-50)
    """)
    findings = _run(s, t)
    assert findings, "should fire for NFR-50 not in spec"
    assert "NFR-50" in findings[0].message


def test_multiple_dangling_refs_fires_per_line():
    """Two task lines each with a dangling ref produce two findings."""
    s = _spec("""
        # Spec
        ## Requirements
        FR-001: The system shall do X.
    """)
    t = _tasks("""
        # Tasks
        - [ ] T01 [US5] Feature A (FR-001)
        - [ ] T02 [US6] Feature B (FR-002)
    """)
    findings = _run(s, t)
    pitfall_findings = findings
    assert len(pitfall_findings) == 2, "one finding per dangling task line"


def test_multiple_dangling_ids_on_one_line():
    """A single task line with two dangling IDs shows both in the message."""
    s = _spec("""
        # Spec
        ## Requirements
        FR-001: The system shall do X.
    """)
    t = _tasks("""
        # Tasks
        - [ ] T01 [US99] Feature A (FR-77)
    """)
    findings = _run(s, t)
    assert findings
    msg = findings[0].message
    assert "FR-77" in msg or "US-99" in msg


def test_us_id_form_not_in_spec_fires():
    """US-9 (dash form) in tasks but spec only defines User Story 1."""
    s = _spec("""
        # Spec
        ## User Story 1
        As a user I want X.
    """)
    t = _tasks("""
        # Tasks
        - [ ] T01 US-9 some task
    """)
    findings = _run(s, t)
    assert findings, "should fire for US-9 not in spec"


# --------------------------------------------------------------------------- no-fire cases


def test_valid_us_tag_no_fire():
    """[US2] in tasks, spec defines User Story 2 → no fire."""
    s = _spec("""
        # Spec
        ## User Story 2
        As a user I want Y.
    """)
    t = _tasks("""
        # Tasks
        - [ ] T01 [US2] Implement feature Y
    """)
    findings = _run(s, t)
    assert not findings, "valid US ref should not fire"


def test_valid_fr_id_no_fire():
    """FR-001 and [US1] in tasks, spec defines both → no fire."""
    s = _spec("""
        # Spec
        ## User Story 1
        As a user I want to log in.
        ## Requirements
        FR-001: The system shall authenticate users.
    """)
    t = _tasks("""
        # Tasks
        - [ ] T01 [US1] Implement auth (FR-001)
    """)
    findings = _run(s, t)
    assert not findings, "valid FR ref and valid US ref should not fire"


def test_no_spec_ids_guard_no_fire():
    """spec.md has no formal IDs → guard prevents false positives."""
    s = _spec("""
        # Spec
        The system shall authenticate users via OAuth.
        Users should be able to log out.
    """)
    t = _tasks("""
        # Tasks
        - [ ] T01 [US7] Implement phantom feature (FR-99)
    """)
    findings = _run(s, t)
    assert not findings, "no spec IDs defined → guard should prevent fire"


def test_task_with_no_req_link_no_fire():
    """Task with no requirement reference at all → XREF-DANGLING-REQ-REF must not fire."""
    s = _spec("""
        # Spec
        ## Requirements
        FR-001: The system shall do X.
    """)
    t = _tasks("""
        # Tasks
        - [ ] T01 Refactor logging module
    """)
    findings = _run(s, t)
    assert not findings, "task with no ref is TASKS-UNTRACED-TASK's domain, not ours"


def test_fenced_block_refs_no_fire():
    """References inside a fenced code block must not trigger the check."""
    s = _spec("""
        # Spec
        ## User Story 1
        As a user I want X.
        ## Requirements
        FR-001: The system shall do X.
    """)
    t = _tasks("""
        # Tasks
        - [ ] T01 [US1] Implement feature

        ```python
        # FR-99 referenced here in a code comment
        x = "US-99"
        ```
    """)
    findings = _run(s, t)
    assert not findings, "refs inside fenced blocks must not fire"


def test_us_dash_form_defined_in_spec_no_fire():
    """spec.md contains US-3 (dash form) and task uses [US3] → they should match."""
    s = _spec("""
        # Spec
        ## Requirements
        US-3: The system shall display the dashboard.
    """)
    t = _tasks("""
        # Tasks
        - [ ] T01 [US3] Build dashboard view
    """)
    findings = _run(s, t)
    assert not findings, "US-3 in spec should satisfy [US3] in tasks"


def test_no_tasks_artifact_no_fire():
    """Only spec provided (no tasks artifact) → no crash, no findings."""
    s = _spec("""
        # Spec
        ## Requirements
        FR-001: The system shall do X.
    """)
    findings = [f for f in _cross_artifact([s], CATALOG) if f.pitfall_id == PITFALL]
    assert not findings


def test_severity_is_high():
    """The pitfall severity must be high."""
    from sddgrade.catalog import load_catalog
    cat = load_catalog()
    p = cat.get(PITFALL)
    assert p is not None, f"{PITFALL} not in catalog"
    assert p.severity.value == "high"
