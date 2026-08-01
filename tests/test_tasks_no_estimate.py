"""Unit tests for TASKS-NO-ESTIMATE pitfall (INVEST Estimable criterion)."""

from __future__ import annotations

import textwrap

from sddgrade.adapters.base import parse_sections
from sddgrade.catalog import load_catalog
from sddgrade.engine.lint import _tasks_no_estimate
from sddgrade.model import Artifact, ArtifactType

CATALOG = load_catalog()
PITFALL = "TASKS-NO-ESTIMATE"


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


# ── fires ────────────────────────────────────────────────────────────────────


def test_fires_three_tasks_no_estimate():
    """3+ T## tasks with no estimate annotation → fires."""
    art = _tasks("""
        ## Tasks

        - [ ] T01 [US1] Implement login endpoint
        - [ ] T02 [US1] Add password hashing
        - [ ] T03 [US2] Write migration script
    """)
    findings = _tasks_no_estimate(art, CATALOG)
    assert PITFALL in ids(findings)


def test_fires_many_tasks_no_estimate():
    """7 T## tasks with no estimate → fires."""
    raw = "## Tasks\n\n"
    for i in range(1, 8):
        raw += f"- [ ] T0{i} [US1] Task number {i}\n"
    art = _tasks(raw)
    findings = _tasks_no_estimate(art, CATALOG)
    assert PITFALL in ids(findings)


def test_finding_anchored_to_first_task_line():
    """Finding line number anchors to first T## task."""
    art = _tasks("""
        ## Tasks

        - [ ] T01 [US1] Implement login endpoint
        - [ ] T02 [US1] Add password hashing
        - [ ] T03 [US2] Write migration script
    """)
    findings = _tasks_no_estimate(art, CATALOG)
    hits = [f for f in findings if f.pitfall_id == PITFALL]
    assert hits
    assert hits[0].line == 3  # first T## checkbox is line 3 (after dedent+strip)


def test_fires_once_even_with_many_tasks():
    """Multiple tasks with no estimate produce exactly one finding."""
    raw = "## Tasks\n\n"
    for i in range(1, 10):
        raw += f"- [ ] T0{i} [US1] Task {i}\n"
    art = _tasks(raw)
    findings = _tasks_no_estimate(art, CATALOG)
    assert ids(findings).count(PITFALL) == 1


# ── silent: estimate present ─────────────────────────────────────────────────


def test_silent_story_points_inline():
    """Story-points annotation inline → silent."""
    art = _tasks("""
        ## Tasks

        - [ ] T01 [US1] Implement login endpoint (3 sp)
        - [ ] T02 [US1] Add password hashing (2 sp)
        - [ ] T03 [US2] Write migration script (1 sp)
    """)
    findings = _tasks_no_estimate(art, CATALOG)
    assert PITFALL not in ids(findings)


def test_silent_story_points_summary_line():
    """sp: annotation anywhere in file → silent."""
    art = _tasks("""
        ## Tasks

        - [ ] T01 [US1] Implement login endpoint
        - [ ] T02 [US1] Add password hashing
        - [ ] T03 [US2] Write migration script

        Total effort: sp: 6
    """)
    findings = _tasks_no_estimate(art, CATALOG)
    assert PITFALL not in ids(findings)


def test_silent_tshirt_bracket_xl():
    """[XL] t-shirt annotation → silent."""
    art = _tasks("""
        ## Tasks

        - [ ] T01 [US1] Implement login endpoint [XL]
        - [ ] T02 [US1] Add password hashing
        - [ ] T03 [US2] Write migration script
    """)
    findings = _tasks_no_estimate(art, CATALOG)
    assert PITFALL not in ids(findings)


def test_silent_tshirt_bracket_xxl():
    """[XXL] t-shirt annotation → silent."""
    art = _tasks("""
        ## Tasks

        - [ ] T01 [US1] First task [XXL]
        - [ ] T02 [US1] Second task
        - [ ] T03 [US2] Third task
    """)
    findings = _tasks_no_estimate(art, CATALOG)
    assert PITFALL not in ids(findings)


def test_silent_hours_annotation():
    """Hours annotation → silent."""
    art = _tasks("""
        ## Tasks

        - [ ] T01 [US1] Implement login (2h)
        - [ ] T02 [US1] Add hashing
        - [ ] T03 [US2] Write migration
    """)
    findings = _tasks_no_estimate(art, CATALOG)
    assert PITFALL not in ids(findings)


def test_silent_days_annotation():
    """Days annotation anywhere in file → silent."""
    art = _tasks("""
        ## Tasks

        - [ ] T01 [US1] Implement login
        - [ ] T02 [US1] Add hashing
        - [ ] T03 [US2] Write migration

        Estimate: 3 days total.
    """)
    findings = _tasks_no_estimate(art, CATALOG)
    assert PITFALL not in ids(findings)


def test_silent_size_keyword():
    """'size: M' annotation → silent."""
    art = _tasks("""
        ## Tasks

        - [ ] T01 [US1] Implement login
        - [ ] T02 [US1] Add hashing
        - [ ] T03 [US2] Write migration

        size: M
    """)
    findings = _tasks_no_estimate(art, CATALOG)
    assert PITFALL not in ids(findings)


def test_silent_pts_annotation():
    """pts annotation → silent."""
    art = _tasks("""
        ## Tasks

        - [ ] T01 [US1] Implement login
        - [ ] T02 [US1] Add hashing
        - [ ] T03 [US2] Write migration

        Total: 5 pts
    """)
    findings = _tasks_no_estimate(art, CATALOG)
    assert PITFALL not in ids(findings)


# ── silent: too few tasks ─────────────────────────────────────────────────────


def test_silent_fewer_than_three_tasks():
    """Only 2 T## tasks → too few to require estimation, silent."""
    art = _tasks("""
        ## Tasks

        - [ ] T01 [US1] Implement login endpoint
        - [ ] T02 [US2] Write migration script
    """)
    findings = _tasks_no_estimate(art, CATALOG)
    assert PITFALL not in ids(findings)


def test_silent_zero_tasks():
    """No checkbox tasks → silent."""
    art = _tasks("""
        ## Tasks

        No task items here.
    """)
    findings = _tasks_no_estimate(art, CATALOG)
    assert PITFALL not in ids(findings)


# ── silent: fenced blocks excluded ───────────────────────────────────────────


def test_fenced_tasks_not_counted():
    """Tasks inside fenced block don't count toward the threshold."""
    art = _tasks("""
        ## Tasks

        - [ ] T01 [US1] Real task one
        - [ ] T02 [US1] Real task two

        ```
        - [ ] T03 [US3] Fenced example task
        - [ ] T04 [US4] Fenced example task
        - [ ] T05 [US4] Fenced example task
        ```
    """)
    # Only 2 real tasks → threshold not met → silent
    findings = _tasks_no_estimate(art, CATALOG)
    assert PITFALL not in ids(findings)


# ── silent: wrong artifact type ───────────────────────────────────────────────


def test_silent_on_spec_artifact():
    """Spec artifact with T## lines → not a tasks artifact, silent."""
    content = (
        "- [ ] T01 [US1] Thing one\n"
        "- [ ] T02 [US2] Thing two\n"
        "- [ ] T03 [US3] Thing three\n"
    )
    art = _spec(content)
    findings = _tasks_no_estimate(art, CATALOG)
    assert PITFALL not in ids(findings)
