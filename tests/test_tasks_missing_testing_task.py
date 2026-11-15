"""Unit tests for TASKS-MISSING-TESTING-TASK pitfall."""

from __future__ import annotations

import textwrap

from sddgrade.adapters.base import parse_sections
from sddgrade.catalog import load_catalog
from sddgrade.engine.lint import _tasks_missing_testing_task
from sddgrade.model import Artifact, ArtifactType

CATALOG = load_catalog()
PITFALL = "TASKS-MISSING-TESTING-TASK"


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


def test_fires_five_impl_tasks_no_testing():
    """5 implementation tasks with no testing task → fires."""
    art = _tasks("""
        ## Tasks

        - [ ] T01 [US1] Implement login endpoint
        - [ ] T02 [US1] Add password hashing middleware
        - [ ] T03 [US2] Create user profile page
        - [ ] T04 [US2] Add database migrations
        - [ ] T05 [US3] Wire up email notifications
    """)
    findings = _tasks_missing_testing_task(art, CATALOG)
    assert PITFALL in ids(findings)


def test_fires_ten_tasks_no_testing():
    """10 implementation tasks with no testing task → fires."""
    raw = "## Tasks\n\n"
    for i in range(1, 11):
        raw += f"- [ ] T{i:02d} [US1] Implement feature {i}\n"
    art = _tasks(raw)
    findings = _tasks_missing_testing_task(art, CATALOG)
    assert PITFALL in ids(findings)


def test_fires_testing_vocab_in_prose_only():
    """Testing word in prose line (not task line) does not silence the check."""
    art = _tasks("""
        ## Tasks

        Testing is an important aspect of this feature.

        - [ ] T01 [US1] Implement login endpoint
        - [ ] T02 [US1] Add password hashing
        - [ ] T03 [US2] Create profile page
        - [ ] T04 [US2] Add database migrations
        - [ ] T05 [US3] Wire up email notifications
    """)
    findings = _tasks_missing_testing_task(art, CATALOG)
    assert PITFALL in ids(findings)


def test_fires_testing_vocab_in_heading_only():
    """Testing mention in heading only (not a T## task line) does not silence."""
    art = _tasks("""
        ## Testing Strategy

        - [ ] T01 [US1] Implement login endpoint
        - [ ] T02 [US1] Add password hashing
        - [ ] T03 [US2] Create profile page
        - [ ] T04 [US2] Add database migrations
        - [ ] T05 [US3] Wire up email notifications
    """)
    findings = _tasks_missing_testing_task(art, CATALOG)
    assert PITFALL in ids(findings)


def test_fires_exactly_once():
    """Finding is emitted exactly once regardless of task count."""
    raw = "## Tasks\n\n"
    for i in range(1, 9):
        raw += f"- [ ] T{i:02d} [US1] Build feature {i}\n"
    art = _tasks(raw)
    findings = _tasks_missing_testing_task(art, CATALOG)
    assert ids(findings).count(PITFALL) == 1


# ── silent ───────────────────────────────────────────────────────────────────


def test_silent_fewer_than_five_tasks():
    """Only 4 T## tasks — threshold not met → silent."""
    art = _tasks("""
        ## Tasks

        - [ ] T01 [US1] Implement login endpoint
        - [ ] T02 [US1] Add password hashing
        - [ ] T03 [US2] Create profile page
        - [ ] T04 [US2] Add database migrations
    """)
    findings = _tasks_missing_testing_task(art, CATALOG)
    assert PITFALL not in ids(findings)


def test_silent_task_with_tests_word():
    """A T## task line containing 'tests' silences the check."""
    art = _tasks("""
        ## Tasks

        - [ ] T01 [US1] Implement login endpoint
        - [ ] T02 [US1] Add password hashing
        - [ ] T03 [US2] Create profile page
        - [ ] T04 [US2] Add database migrations
        - [ ] T05 [US1] Write tests for the login flow
    """)
    findings = _tasks_missing_testing_task(art, CATALOG)
    assert PITFALL not in ids(findings)


def test_silent_task_with_unit_test():
    """A T## task with 'unit test' in the description silences the check."""
    art = _tasks("""
        ## Tasks

        - [ ] T01 [US1] Implement login endpoint
        - [ ] T02 [US1] Add password hashing
        - [ ] T03 [US2] Create profile page
        - [ ] T04 [US2] Add database migrations
        - [ ] T05 [US1] Add unit tests for authentication module
    """)
    findings = _tasks_missing_testing_task(art, CATALOG)
    assert PITFALL not in ids(findings)


def test_silent_task_with_integration_testing():
    """A T## task with 'integration testing' silences the check."""
    art = _tasks("""
        ## Tasks

        - [ ] T01 [US1] Implement login endpoint
        - [ ] T02 [US1] Add password hashing
        - [ ] T03 [US2] Create profile page
        - [ ] T04 [US2] Add database migrations
        - [ ] T05 [US3] Integration testing for the payment flow
    """)
    findings = _tasks_missing_testing_task(art, CATALOG)
    assert PITFALL not in ids(findings)


def test_silent_task_with_verify():
    """A T## task with 'verify' silences the check."""
    art = _tasks("""
        ## Tasks

        - [ ] T01 [US1] Implement login endpoint
        - [ ] T02 [US1] Add password hashing
        - [ ] T03 [US2] Create profile page
        - [ ] T04 [US2] Add database migrations
        - [ ] T05 [US3] Verify that login redirects work correctly
    """)
    findings = _tasks_missing_testing_task(art, CATALOG)
    assert PITFALL not in ids(findings)


def test_silent_task_with_validate():
    """A T## task with 'validate' silences the check."""
    art = _tasks("""
        ## Tasks

        - [ ] T01 [US1] Implement login endpoint
        - [ ] T02 [US1] Add password hashing
        - [ ] T03 [US2] Create profile page
        - [ ] T04 [US2] Add database migrations
        - [ ] T05 [US3] Validate payment processing end-to-end
    """)
    findings = _tasks_missing_testing_task(art, CATALOG)
    assert PITFALL not in ids(findings)


def test_silent_task_with_e2e():
    """A T## task with 'e2e' silences the check."""
    art = _tasks("""
        ## Tasks

        - [ ] T01 [US1] Implement login endpoint
        - [ ] T02 [US1] Add password hashing
        - [ ] T03 [US2] Create profile page
        - [ ] T04 [US2] Add database migrations
        - [ ] T05 [US3] Run e2e tests for user registration flow
    """)
    findings = _tasks_missing_testing_task(art, CATALOG)
    assert PITFALL not in ids(findings)


def test_silent_zero_tasks():
    """No T## tasks at all → threshold not met → silent."""
    art = _tasks("""
        ## Tasks

        No task items here yet.
    """)
    findings = _tasks_missing_testing_task(art, CATALOG)
    assert PITFALL not in ids(findings)


def test_silent_wrong_artifact_type():
    """Spec artifact with T## lines → not a tasks artifact → silent."""
    content = "\n".join(
        f"- [ ] T{i:02d} [US1] Implement feature {i}" for i in range(1, 7)
    )
    art = _spec(content)
    findings = _tasks_missing_testing_task(art, CATALOG)
    assert PITFALL not in ids(findings)


def test_silent_fenced_tasks_not_counted_for_threshold():
    """Real tasks count < 5 when most are inside a fenced block → silent."""
    art = _tasks("""
        ## Tasks

        - [ ] T01 [US1] Implement login
        - [ ] T02 [US1] Add hashing

        ```
        - [ ] T03 [US2] Create page
        - [ ] T04 [US2] Add migrations
        - [ ] T05 [US3] Wire notifications
        ```
    """)
    # Only 2 non-fenced T## tasks → threshold not met → silent
    findings = _tasks_missing_testing_task(art, CATALOG)
    assert PITFALL not in ids(findings)
