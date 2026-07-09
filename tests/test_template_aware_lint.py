"""Regression tests for issue #69: template-aware lint checks.

Phantom findings on canonical Spec-Kit layouts must NOT fire; real issues
on genuine author-written content MUST still fire.
"""

from __future__ import annotations

from sddgrade.adapters.base import parse_sections
from sddgrade.catalog import load_catalog
from sddgrade.engine.lint import _spec_checks, _plan_checks, _count_real_clarification_markers
from sddgrade.model import Artifact, ArtifactType


def _spec(text: str) -> Artifact:
    return Artifact(
        path="spec.md", type=ArtifactType.SPEC, feature_id="x",
        raw=text, sections=parse_sections(text),
    )


def _plan(text: str) -> Artifact:
    return Artifact(
        path="plan.md", type=ArtifactType.PLAN, feature_id="x",
        raw=text, sections=parse_sections(text),
    )


def _ids(findings: list) -> set[str]:
    return {f.pitfall_id for f in findings if f.pitfall_id}


CATALOG = load_catalog()


# ─── SPEC-UNRESOLVED-CLARIFICATION ────────────────────────────────────────────────

def test_real_clarification_marker_is_counted():
    raw = "- Entity: [NEEDS CLARIFICATION: what fields?]\n"
    assert _count_real_clarification_markers(raw) == 1


def test_blockquote_clarification_not_counted():
    """Template instruction blocks (leading '>') must not count as real markers."""
    raw = (
        "> For AI Generation: replace all [NEEDS CLARIFICATION ...] with real text.\n"
        "> See the [NEEDS CLARIFICATION] guide.\n"
    )
    assert _count_real_clarification_markers(raw) == 0


def test_checklist_reference_not_counted():
    """The checklist item 'No [NEEDS CLARIFICATION] markers remain' must not count."""
    raw = "- [ ] No [NEEDS CLARIFICATION] markers remain\n"
    assert _count_real_clarification_markers(raw) == 0


def test_template_with_phantom_markers_no_finding():
    """A clean spec with only template boilerplate markers must not trigger the pitfall."""
    raw = (
        "# Feature Specification: Auth\n\n"
        "## User Scenarios\n\n"
        "### Primary User Story\n"
        "As a user, I can log in.\n\n"
        "### Acceptance Scenarios\n"
        "Given I have valid credentials, when I submit, then I am authenticated.\n\n"
        "## Requirements\n\n"
        "- FR-001: The system shall authenticate users via OAuth.\n\n"
        "## Success Criteria\n\n"
        "- 99% of logins complete within 2 seconds.\n\n"
        "## Checklist\n\n"
        "> For AI Generation: fill in each section before finalising.\n"
        "> All [NEEDS CLARIFICATION ...] blocks must be resolved.\n"
        "- [ ] No [NEEDS CLARIFICATION] markers remain\n"
    )
    findings = _spec_checks(_spec(raw), CATALOG)
    assert "SPEC-UNRESOLVED-CLARIFICATION" not in _ids(findings), findings


def test_real_clarification_in_spec_triggers_finding():
    raw = (
        "# Feature Specification: Auth\n\n"
        "## User Scenarios\n\n"
        "### Primary User Story\n"
        "As a user, I can do x.\n"
        "Given I am logged in, When I click, Then it works.\n\n"
        "## Requirements\n\n"
        "- Entity: [NEEDS CLARIFICATION: define the entity fields]\n\n"
        "## Success Criteria\n\n"
        "- 99% within 2 seconds.\n"
    )
    findings = _spec_checks(_spec(raw), CATALOG)
    assert "SPEC-UNRESOLVED-CLARIFICATION" in _ids(findings), findings


# ─── SPEC-MISSING-ACCEPTANCE ───────────────────────────────────────────────────

def test_acceptance_in_sibling_section_is_recognized():
    """Canonical Spec-Kit layout: ### Acceptance Scenarios sibling to ### Primary User Story."""
    raw = (
        "# Feature Specification: Auth\n\n"
        "## User Scenarios\n\n"
        "### Primary User Story\n"
        "As a user, I can log in to access my account.\n\n"
        "### Acceptance Scenarios\n"
        "Given I have valid credentials, when I submit the form, then I am redirected.\n\n"
        "## Requirements\n\n"
        "- FR-001: The system shall authenticate users.\n\n"
        "## Success Criteria\n\n"
        "- 99% of logins complete within 2 seconds.\n"
    )
    findings = _spec_checks(_spec(raw), CATALOG)
    assert "SPEC-MISSING-ACCEPTANCE" not in _ids(findings), findings


def test_acceptance_inline_in_story_body_still_works():
    """Acceptance criteria inline in the story section body must still be recognized."""
    raw = (
        "# Feature Specification: Auth\n\n"
        "## User Scenarios\n\n"
        "### User Story 1\n"
        "As a user, I can log in.\n"
        "Given valid credentials, when I submit, then I am authenticated.\n\n"
        "## Requirements\n\n"
        "- FR-001: The system shall authenticate users.\n\n"
        "## Success Criteria\n\n"
        "- 99% within 2 seconds.\n"
    )
    findings = _spec_checks(_spec(raw), CATALOG)
    assert "SPEC-MISSING-ACCEPTANCE" not in _ids(findings), findings


def test_story_with_no_acceptance_anywhere_triggers_finding():
    """A user story with no Given/When/Then in any sibling section must still be flagged."""
    raw = (
        "# Feature Specification: Auth\n\n"
        "## User Scenarios\n\n"
        "### User Story 1\n"
        "As a user, I can log in.\n"
        "TODO: write acceptance criteria.\n\n"
        "## Requirements\n\n"
        "- FR-001: The system shall authenticate users.\n\n"
        "## Success Criteria\n\n"
        "- 99% within 2 seconds.\n"
    )
    findings = _spec_checks(_spec(raw), CATALOG)
    assert "SPEC-MISSING-ACCEPTANCE" in _ids(findings), findings


def test_acceptance_in_nested_scenarios_section_is_recognized():
    """Nested 'Scenarios' section under a user story also satisfies the check."""
    raw = (
        "# Feature Specification: Auth\n\n"
        "## User Scenarios\n\n"
        "### Primary User Story\n"
        "As a user, I can log in.\n\n"
        "#### Scenarios\n"
        "- Given I am on the login page, when I enter valid creds, then I am in.\n\n"
        "## Requirements\n\n"
        "- FR-001: The system shall authenticate users.\n\n"
        "## Success Criteria\n\n"
        "- 99% within 2 seconds.\n"
    )
    findings = _spec_checks(_spec(raw), CATALOG)
    assert "SPEC-MISSING-ACCEPTANCE" not in _ids(findings), findings


def test_plan_blockquote_clarification_not_counted():
    """Template instruction blockquotes in plan.md must not count as real markers."""
    raw = (
        "# Plan\n\n"
        "## Summary\n\nThe plan.\n\n"
        "## Technical Context\n\nContext.\n\n"
        "## Constitution Check\n\nPass — no violations.\n\n"
        "## Project Structure\n\nStructure.\n\n"
        "> For AI Generation: resolve [NEEDS CLARIFICATION ...] items before submitting.\n"
    )
    findings = _plan_checks(_plan(raw), CATALOG)
    assert "SPEC-UNRESOLVED-CLARIFICATION" not in _ids(findings), findings
