"""Tests for XREF-AC-NO-TASK — AC-NNN defined in spec.md but not referenced by any task."""
from __future__ import annotations

import textwrap

from sddgrade.adapters.base import parse_sections
from sddgrade.catalog import load_catalog
from sddgrade.engine.lint import _cross_artifact
from sddgrade.model import Artifact, ArtifactType

CATALOG = load_catalog()
PITFALL = "XREF-AC-NO-TASK"


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


# ───────────────────────────────────────────── fire cases ───────────────────────────────────────────────


def test_ac_in_spec_not_in_tasks_fires():
    """AC-001 defined in spec but no task line references it."""
    s = _spec("""
        # Spec
        ## Acceptance Criteria
        AC-001: The login page must display within 2 seconds.
    """)
    t = _tasks("""
        # Tasks
        - [ ] T01 Implement login page
    """)
    findings = _run(s, t)
    assert findings, "Expected XREF-AC-NO-TASK to fire"
    assert "AC-001" in findings[0].message


def test_multiple_ac_ids_none_in_tasks_fires():
    """AC-001 and AC-002 both defined in spec; neither referenced in tasks."""
    s = _spec("""
        # Spec
        ## Acceptance Criteria
        AC-001: Must load in under 2s.
        AC-002: Must be mobile responsive.
    """)
    t = _tasks("""
        # Tasks
        - [ ] T01 Build frontend
    """)
    findings = _run(s, t)
    assert findings
    msg = findings[0].message
    assert "AC-001" in msg
    assert "AC-002" in msg


def test_some_ac_ids_missing_fires():
    """AC-001 referenced in tasks but AC-002 is not — finding lists AC-002."""
    s = _spec("""
        # Spec
        ## Acceptance Criteria
        AC-001: System logs all errors.
        AC-002: Errors must include a correlation ID.
    """)
    t = _tasks("""
        # Tasks
        - [ ] T01 [AC-001] Implement error logger
    """)
    findings = _run(s, t)
    assert findings
    assert "AC-002" in findings[0].message
    assert "AC-001" not in findings[0].message


def test_finding_anchored_to_spec_path():
    """Finding is anchored to spec.md, not tasks.md."""
    s = _spec("""
        # Spec
        ## Acceptance Criteria
        AC-010: System must support OAuth 2.0.
    """)
    t = _tasks("""
        # Tasks
        - [ ] T01 Build auth flow
    """)
    findings = _run(s, t)
    assert findings
    assert findings[0].artifact_path == "spec.md"


def test_more_than_three_orphans_truncated():
    """When more than 3 AC IDs are orphaned, the message truncates with (+N more)."""
    acs = "\n".join(f"AC-{i:03d}: Criterion {i}." for i in range(1, 7))
    s = _spec(f"# Spec\n## Acceptance Criteria\n{acs}")
    t = _tasks("# Tasks\n- [ ] T01 Do everything")
    findings = _run(s, t)
    assert findings
    assert "(+" in findings[0].message


# ───────────────────────────────────────────── silent cases ─────────────────────────────────────────────


def test_all_ac_ids_referenced_silent():
    """All AC-NNN IDs in spec are referenced in tasks — no finding."""
    s = _spec("""
        # Spec
        ## Acceptance Criteria
        AC-001: Feature loads in 2s.
        AC-002: Feature works on mobile.
    """)
    t = _tasks("""
        # Tasks
        - [ ] T01 [AC-001] Implement fast load
        - [ ] T02 [AC-002] Responsive layout
    """)
    assert _run(s, t) == []


def test_no_ac_ids_in_spec_silent():
    """Spec has no AC-NNN identifiers — guard skips, no finding."""
    s = _spec("""
        # Spec
        ## Requirements
        The system shall support login.
        The system shall support logout.
    """)
    t = _tasks("""
        # Tasks
        - [ ] T01 Implement login
    """)
    assert _run(s, t) == []


def test_ac_id_in_fenced_block_not_collected():
    """AC-NNN inside a fenced code block in spec is not collected as a defined ID."""
    s = _spec("""
        # Spec
        ## Notes
        ```
        AC-001: example criterion only
        ```
        The system shall support login.
    """)
    t = _tasks("""
        # Tasks
        - [ ] T01 Implement login
    """)
    assert _run(s, t) == []


def test_ac_id_in_heading_not_collected():
    """AC-NNN on a heading line is not collected as a defined ID (headings are structural)."""
    s = _spec("""
        # Spec
        ## AC-001 Acceptance Criteria
        The system shall load in under 2 seconds.
    """)
    t = _tasks("""
        # Tasks
        - [ ] T01 Performance work
    """)
    assert _run(s, t) == []


def test_ac_referenced_in_non_task_line_still_fires():
    """AC-NNN mentioned in a prose tasks line (no checkbox) is not counted as a task reference."""
    s = _spec("""
        # Spec
        ## Acceptance Criteria
        AC-001: Must respond within 200ms.
    """)
    t = _tasks("""
        # Tasks
        See AC-001 for full criteria.
        - [ ] T01 Performance optimisation
    """)
    findings = _run(s, t)
    assert findings, "Expected XREF-AC-NO-TASK: non-task prose mention should not count"
    assert "AC-001" in findings[0].message


def test_ac_in_fenced_task_block_not_counted():
    """AC-NNN inside a fenced block in tasks.md does not count as a task reference."""
    s = _spec("""
        # Spec
        ## Acceptance Criteria
        AC-001: Must respond within 200ms.
    """)
    t = _tasks("""
        # Tasks
        ```
        - [ ] T01 [AC-001] example task
        ```
        - [ ] T01 Performance work
    """)
    findings = _run(s, t)
    assert findings
    assert "AC-001" in findings[0].message


def test_ac_case_insensitive():
    """AC-NNN matching is case-insensitive (ac-001 in tasks matches AC-001 in spec)."""
    s = _spec("""
        # Spec
        ## Acceptance Criteria
        AC-001: Must respond within 200ms.
    """)
    t = _tasks("""
        # Tasks
        - [ ] T01 [ac-001] Performance work
    """)
    assert _run(s, t) == []


def test_single_pitfall_id_in_catalog():
    """XREF-AC-NO-TASK is present in the catalog."""
    assert PITFALL in CATALOG
