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


# ─── Canonical Spec-Kit template-shaped spec (end-to-end regression, #69) ─────

# Verbatim template machinery a freshly generated Spec-Kit spec retains: a fenced
# 'Execution Flow (main)' body, the 'For AI Generation' instruction list, sibling
# '### Acceptance Scenarios', review-checklist lines — plus exactly ONE genuine
# author-written [NEEDS CLARIFICATION: ...] marker (FR-003).
CANONICAL_SPEC = """\
# Feature Specification: Typed Market Proxy

**Feature Branch**: `001-typed-proxy`
**Status**: Draft

## Execution Flow (main)
```
1. Parse user description from Input
   → If empty: ERROR "No feature description provided"
2. Extract key concepts from description
3. For each unclear aspect:
   → Mark with [NEEDS CLARIFICATION: specific question]
4. Fill User Scenarios & Testing section
5. Generate Functional Requirements
   → Each requirement must be testable
6. Run Review Checklist
   → If any [NEEDS CLARIFICATION]: WARN "Spec has uncertainties"
7. Return: SUCCESS (spec ready for planning)
```

---

## ⚡ Quick Guidelines
- ✅ Focus on WHAT users need and WHY
- ❌ Avoid HOW to implement

### For AI Generation
When creating this spec from a user prompt:
1. **Mark all ambiguities**: Use [NEEDS CLARIFICATION: specific question] for any assumption you'd need to make
2. **Don't guess**: If the prompt doesn't specify something, mark it

---

## User Scenarios & Testing *(mandatory)*

### Primary User Story
As an API consumer, I want a typed proxy for market data so that I can build
clients without hand-writing response types.

### Acceptance Scenarios
1. **Given** a running proxy, **When** I request the markets list, **Then** I receive a schema-validated response.
2. **Given** an invalid request, **When** I submit it, **Then** I receive a 400 with a machine-readable error.

### Edge Cases
- What happens when the upstream API is unreachable?

## Requirements *(mandatory)*

### Functional Requirements
- **FR-001**: System MUST proxy market data requests to the upstream API.
- **FR-002**: System MUST validate every response against its published schema.
- **FR-003**: System MUST authenticate consumers via [NEEDS CLARIFICATION: auth method not specified - API key or OAuth?]

## Success Criteria

- 95% of proxied requests complete within 300 ms.

## Review & Acceptance Checklist

- [ ] No implementation details (languages, frameworks, APIs)
- [ ] No [NEEDS CLARIFICATION] markers remain
- [x] Requirements are testable and unambiguous

## Execution Status

- [x] User description parsed
- [x] Key concepts extracted
- [x] Review checklist passed
"""


def test_canonical_spec_counts_exactly_one_real_marker():
    assert _count_real_clarification_markers(CANONICAL_SPEC) == 1


def test_canonical_spec_reports_one_unresolved_clarification():
    findings = _spec_checks(_spec(CANONICAL_SPEC), CATALOG)
    clar = [f for f in findings if f.pitfall_id == "SPEC-UNRESOLVED-CLARIFICATION"]
    assert len(clar) == 1, clar
    assert "1 unresolved" in clar[0].message, clar[0].message


def test_canonical_spec_has_no_missing_acceptance_finding():
    findings = _spec_checks(_spec(CANONICAL_SPEC), CATALOG)
    assert "SPEC-MISSING-ACCEPTANCE" not in _ids(findings), findings


CANONICAL_TEMPLATE = """\
# Feature Specification: [FEATURE NAME]

## Execution Flow (main)
```
1. Parse user description from Input
```

## ⚡ Quick Guidelines
- ✅ Focus on WHAT users need and WHY

## User Scenarios & Testing *(mandatory)*

### Primary User Story

### Acceptance Scenarios

## Requirements *(mandatory)*

### Functional Requirements

## Review & Acceptance Checklist

## Execution Status
"""


def test_template_derived_required_sections_exclude_scaffolding(tmp_path):
    """The speckit adapter must not require Execution Flow / Quick Guidelines /
    Execution Status even when deriving sections from an on-disk template (#69)."""
    from sddgrade.adapters.speckit import SpecKitAdapter

    tpl_dir = tmp_path / ".specify" / "templates"
    tpl_dir.mkdir(parents=True)
    (tpl_dir / "spec-template.md").write_text(CANONICAL_TEMPLATE, encoding="utf-8")

    required = SpecKitAdapter().required_sections(ArtifactType.SPEC, tmp_path)
    lowered = [r.lower() for r in required]
    assert not any("execution flow" in r for r in lowered), required
    assert not any("quick guidelines" in r for r in lowered), required
    assert not any("execution status" in r for r in lowered), required
    assert any("user scenarios" in r for r in lowered), required
    assert any("requirements" in r for r in lowered), required


def test_spec_without_scaffolding_sections_has_no_missing_section_findings(tmp_path):
    """A spec that (correctly) drops the template machinery must not be penalised
    for the three scaffolding sections."""
    from sddgrade.adapters.speckit import SpecKitAdapter
    from sddgrade.engine.lint import _required_sections

    tpl_dir = tmp_path / ".specify" / "templates"
    tpl_dir.mkdir(parents=True)
    (tpl_dir / "spec-template.md").write_text(CANONICAL_TEMPLATE, encoding="utf-8")

    cleaned = (
        "# Feature Specification: Typed Market Proxy\n\n"
        "## User Scenarios & Testing *(mandatory)*\n\n"
        "### Primary User Story\nAs a user, I can query markets.\n\n"
        "### Acceptance Scenarios\nGiven a proxy, when I query, then I get typed data.\n\n"
        "## Requirements *(mandatory)*\n\n"
        "### Functional Requirements\n- **FR-001**: System MUST proxy requests.\n\n"
        "## Review & Acceptance Checklist\n\n- [x] Requirements are testable\n"
    )
    findings = _required_sections(_spec(cleaned), SpecKitAdapter(), tmp_path)
    scaffolding_hits = [
        f for f in findings
        if any(
            t in f.message.lower()
            for t in ("execution flow", "quick guidelines", "execution status")
        )
    ]
    assert scaffolding_hits == [], scaffolding_hits
