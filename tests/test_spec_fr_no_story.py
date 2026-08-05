"""Tests for SPEC-FR-NO-STORY pitfall.

The check fires when a spec organises stories under US-NNN headings AND has
FR-/NFR- lines that sit outside every US-NNN section with no [US#] tag.

Guard: only fires when ≥1 section title begins with 'US-NNN' (literal prefix).
       Specs using 'User Story N' headings (standard Spec-Kit) are not checked.
"""

from __future__ import annotations

import pytest

from sddgrade.adapters.base import parse_sections
from sddgrade.catalog import load_catalog
from sddgrade.engine.lint import _spec_fr_no_story
from sddgrade.model import Artifact, ArtifactType


def _make_spec(raw: str) -> Artifact:
    return Artifact(
        path="spec.md",
        type=ArtifactType.SPEC,
        raw=raw,
        sections=parse_sections(raw),
    )


CATALOG = load_catalog()


# ---------------------------------------------------------------------------
# FIRE cases — check should trigger
# ---------------------------------------------------------------------------


def test_fr_outside_us_section_no_tag_fires() -> None:
    """FR line in a Requirements section (outside US-NNN) with no [US#] tag → fires."""
    spec = _make_spec(
        "# Feature Spec\n\n"
        "## US-001: Login\n\n"
        "As a user, I want to log in.\n\n"
        "## Requirements\n\n"
        "- FR-001: The system shall authenticate the user.\n"
    )
    findings = _spec_fr_no_story(spec, CATALOG)
    assert len(findings) == 1
    assert "SPEC-FR-NO-STORY" in findings[0].pitfall_id
    assert "FR-" in findings[0].message


def test_nfr_outside_us_section_fires() -> None:
    """NFR line outside US-NNN section with no [US#] → fires."""
    spec = _make_spec(
        "# Feature\n\n"
        "## US-001: Dashboard\n\n"
        "Story content.\n\n"
        "## Non-Functional Requirements\n\n"
        "- NFR-001: Response time shall be under 200ms.\n"
    )
    findings = _spec_fr_no_story(spec, CATALOG)
    assert len(findings) == 1
    assert findings[0].pitfall_id == "SPEC-FR-NO-STORY"


def test_multiple_orphaned_fr_lines_fires_once() -> None:
    """Multiple orphaned FR lines → single aggregate finding at first offending line."""
    spec = _make_spec(
        "# Feature\n\n"
        "## US-001: Login\n\n"
        "Story.\n\n"
        "## Requirements\n\n"
        "- FR-001: The system shall do X.\n"
        "- FR-002: The system shall do Y.\n"
        "- FR-003: The system shall do Z.\n"
    )
    findings = _spec_fr_no_story(spec, CATALOG)
    assert len(findings) == 1
    assert "3 FR-/NFR-" in findings[0].message


def test_mixed_tagged_and_untagged_fr_lines_fires() -> None:
    """Some FR lines have [US1] tag, others don't → fires for the untagged ones."""
    spec = _make_spec(
        "# Feature\n\n"
        "## US-001: Login\n\n"
        "As a user, I want to log in.\n\n"
        "## Requirements\n\n"
        "- FR-001: The system shall authenticate. [US1]\n"
        "- FR-002: The system shall audit log every login.\n"
    )
    findings = _spec_fr_no_story(spec, CATALOG)
    assert len(findings) == 1
    assert "1 FR-/NFR-" in findings[0].message


def test_fr_in_fenced_block_is_skipped() -> None:
    """FR lines inside fenced code blocks should not be flagged."""
    spec = _make_spec(
        "# Feature\n\n"
        "## US-001: Login\n\n"
        "Story.\n\n"
        "## Example\n\n"
        "```\n"
        "- FR-001: The system shall do X.\n"
        "```\n"
    )
    findings = _spec_fr_no_story(spec, CATALOG)
    assert findings == []


# ---------------------------------------------------------------------------
# SILENT cases — check should NOT trigger
# ---------------------------------------------------------------------------


def test_no_us_nnn_headings_silent() -> None:
    """Standard 'User Story N' headings → guard does not fire (not US-NNN format)."""
    spec = _make_spec(
        "# Feature Spec: Password Reset\n\n"
        "## User Scenarios & Testing\n\n"
        "### User Story 1 - Reset password\n\n"
        "As a user, I want to reset my password.\n\n"
        "## Requirements\n\n"
        "### Functional Requirements\n\n"
        "- FR-001: The system shall email a reset link.\n"
        "- FR-002: The system shall expire the link after 30 minutes.\n"
    )
    findings = _spec_fr_no_story(spec, CATALOG)
    assert findings == []


def test_fr_inside_us_section_silent() -> None:
    """FR line nested inside a US-NNN section → no finding."""
    spec = _make_spec(
        "# Feature\n\n"
        "## US-001: Login\n\n"
        "As a user, I want to log in.\n\n"
        "- FR-001: The system shall authenticate the user via OAuth.\n"
    )
    findings = _spec_fr_no_story(spec, CATALOG)
    assert findings == []


def test_fr_with_us_tag_silent() -> None:
    """FR line outside a US-NNN section but with [US1] tag → no finding."""
    spec = _make_spec(
        "# Feature\n\n"
        "## US-001: Login\n\n"
        "Story.\n\n"
        "## Requirements\n\n"
        "- FR-001: The system shall authenticate via OAuth. [US1]\n"
    )
    findings = _spec_fr_no_story(spec, CATALOG)
    assert findings == []


def test_all_fr_inside_us_sections_silent() -> None:
    """All FR lines inside their respective US-NNN sections → no finding."""
    spec = _make_spec(
        "# Feature\n\n"
        "## US-001: Login\n\n"
        "- FR-001: The system shall authenticate users.\n"
        "- FR-002: The system shall support OAuth.\n\n"
        "## US-002: Dashboard\n\n"
        "- FR-003: The system shall display recent activity.\n"
    )
    findings = _spec_fr_no_story(spec, CATALOG)
    assert findings == []


def test_spec_with_no_fr_lines_silent() -> None:
    """Spec with US-NNN headings but no FR-/NFR- lines → no finding."""
    spec = _make_spec(
        "# Feature\n\n"
        "## US-001: Login\n\n"
        "As a user, I want to log in so that I can access my account.\n\n"
        "Acceptance: the login page renders in under 200ms.\n"
    )
    findings = _spec_fr_no_story(spec, CATALOG)
    assert findings == []


def test_spec_with_no_us_headings_at_all_silent() -> None:
    """Spec with only a Requirements section and FR lines but no user story headings → silent."""
    spec = _make_spec(
        "# Feature\n\n"
        "## Functional Requirements\n\n"
        "- FR-001: The system shall do X.\n"
        "- FR-002: The system shall do Y.\n"
    )
    findings = _spec_fr_no_story(spec, CATALOG)
    assert findings == []


def test_fr_with_multiple_us_tags_silent() -> None:
    """FR line with multiple [US#] tags (covers several stories) → no finding."""
    spec = _make_spec(
        "# Feature\n\n"
        "## US-001: Login\n\n"
        "Story 1.\n\n"
        "## US-002: Logout\n\n"
        "Story 2.\n\n"
        "## Shared Requirements\n\n"
        "- FR-001: The system shall maintain a session audit log. [US1][US2]\n"
    )
    findings = _spec_fr_no_story(spec, CATALOG)
    assert findings == []


def test_non_spec_artifact_silent() -> None:
    """The check only applies to spec artifacts; plan/tasks are ignored."""
    raw = (
        "# Plan\n\n"
        "## US-001: Login\n\n"
        "Deploy step.\n\n"
        "## Requirements\n\n"
        "- FR-001: The system shall do X.\n"
    )
    plan = Artifact(
        path="plan.md",
        type=ArtifactType.PLAN,
        raw=raw,
        sections=parse_sections(raw),
    )
    findings = _spec_fr_no_story(plan, CATALOG)
    assert findings == []
