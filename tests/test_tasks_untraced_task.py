"""Tests for TASKS-UNTRACED-TASK — task lines with no requirement traceability link."""
from __future__ import annotations

import textwrap

from sddgrade.adapters.base import parse_sections
from sddgrade.catalog import load_catalog
from sddgrade.engine.lint import _tasks_untraced_task
from sddgrade.model import Artifact, ArtifactType

CATALOG = load_catalog()
PITFALL = "TASKS-UNTRACED-TASK"


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


def ids(findings):
    return [f.pitfall_id for f in findings]


# --- fire cases ---

def test_task_with_no_link_fires():
    """Task has T## id but no [US#] tag and no FR-/NFR- ref → should fire."""
    art = _tasks("""
        # Tasks

        - [ ] T01 Add logging middleware
    """)
    findings = _tasks_untraced_task(art, CATALOG)
    assert PITFALL in ids(findings)


def test_multiple_untraced_tasks_fires_once():
    """Multiple untraced tasks fire a single finding at the first occurrence."""
    art = _tasks("""
        # Tasks

        - [ ] T01 Add logging middleware
        - [ ] T02 Refactor DB connection pool
        - [x] T03 Deploy to staging
    """)
    findings = _tasks_untraced_task(art, CATALOG)
    assert PITFALL in ids(findings)
    assert len([f for f in findings if f.pitfall_id == PITFALL]) == 1


def test_finding_cites_count():
    """The finding message includes the count of untraced tasks."""
    art = _tasks("""
        # Tasks

        - [ ] T01 Orphan task one
        - [ ] T02 Orphan task two
    """)
    findings = _tasks_untraced_task(art, CATALOG)
    assert any("2" in f.message for f in findings if f.pitfall_id == PITFALL)


# --- pass cases ---

def test_task_with_us_tag_passes():
    """Task with [US3] story tag → should not fire."""
    art = _tasks("""
        # Tasks

        - [ ] T01 Implement login endpoint [US3]
    """)
    findings = _tasks_untraced_task(art, CATALOG)
    assert PITFALL not in ids(findings)


def test_task_with_fr_ref_passes():
    """Task with FR-07 requirement ref → should not fire."""
    art = _tasks("""
        # Tasks

        - [ ] T01 Add rate limiter (FR-07)
    """)
    findings = _tasks_untraced_task(art, CATALOG)
    assert PITFALL not in ids(findings)


def test_task_with_nfr_ref_passes():
    """Task with NFR-02 requirement ref → should not fire."""
    art = _tasks("""
        # Tasks

        - [ ] T01 Add caching layer NFR-02
    """)
    findings = _tasks_untraced_task(art, CATALOG)
    assert PITFALL not in ids(findings)


def test_task_with_ac_ref_passes():
    """Task with AC-05 acceptance-criteria ref → should not fire."""
    art = _tasks("""
        # Tasks

        - [ ] T01 Write test for login flow [AC-05]
    """)
    findings = _tasks_untraced_task(art, CATALOG)
    assert PITFALL not in ids(findings)


def test_task_with_us_ref_format_passes():
    """Task with US-3 dash-format ref → should not fire."""
    art = _tasks("""
        # Tasks

        - [ ] T01 Implement export (US-3)
    """)
    findings = _tasks_untraced_task(art, CATALOG)
    assert PITFALL not in ids(findings)


def test_all_tasks_traced_passes():
    """Mixed tasks all properly traced → should not fire."""
    art = _tasks("""
        # Tasks

        ## Tests for User Story 1
        - [ ] T01 Write unit tests [US1]
        - [ ] T02 Write integration tests (FR-01)

        ## Implementation for User Story 1
        - [ ] T03 Implement login [US1]
        - [ ] T04 Add rate limiter FR-02
    """)
    findings = _tasks_untraced_task(art, CATALOG)
    assert PITFALL not in ids(findings)


def test_mixed_traced_and_untraced_fires():
    """Some tasks traced, some not → fires (counts only untraced)."""
    art = _tasks("""
        # Tasks

        - [ ] T01 Implement login [US1]
        - [ ] T02 Orphan task with no ref
        - [ ] T03 Add caching (NFR-01)
        - [ ] T04 Another orphan
    """)
    findings = _tasks_untraced_task(art, CATALOG)
    assert PITFALL in ids(findings)
    assert any("2" in f.message for f in findings if f.pitfall_id == PITFALL)


# --- edge / exclusion cases ---

def test_checkbox_without_task_id_not_counted():
    """Checkbox lines without a T## id are not counted (TASKS-MALFORMED handles those)."""
    art = _tasks("""
        # Tasks

        - [ ] Write tests without a task id
        - [ ] Deploy without a task id
    """)
    findings = _tasks_untraced_task(art, CATALOG)
    assert PITFALL not in ids(findings)


def test_fenced_block_lines_excluded():
    """Lines inside fenced code blocks are excluded from the check."""
    art = _tasks("""
        # Tasks

        ```
        - [ ] T99 This is example code, not a real task
        ```

        - [ ] T01 Real task [US1]
    """)
    findings = _tasks_untraced_task(art, CATALOG)
    assert PITFALL not in ids(findings)


def test_empty_tasks_passes():
    """Empty tasks file does not fire."""
    art = _tasks("# Tasks\n\nNo tasks yet.")
    findings = _tasks_untraced_task(art, CATALOG)
    assert PITFALL not in ids(findings)


def test_does_not_apply_to_spec():
    """Check only applies to tasks artifacts, not spec."""
    art = _spec("""
        # Spec

        - [ ] T01 This is in a spec, not tasks
    """)
    findings = _tasks_untraced_task(art, CATALOG)
    assert PITFALL not in ids(findings)


def test_completed_task_without_link_fires():
    """Completed (checked) tasks without traceability link also fire."""
    art = _tasks("""
        # Tasks

        - [x] T01 Completed but untraced task
    """)
    findings = _tasks_untraced_task(art, CATALOG)
    assert PITFALL in ids(findings)
