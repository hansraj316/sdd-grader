"""Tests for SPECKIT-CONSTITUTION-CROSSCHECK (issue #79).

Cross-artifact check: plan.md's Constitution Check section must reference at
least one actual principle name from constitution.md. Skips when constitution
is absent, has only placeholder headings, or plan has no Constitution Check
section.
"""

from __future__ import annotations

import pytest

from sddgrade.adapters.base import parse_sections
from sddgrade.catalog import load_catalog
from sddgrade.engine.lint import _constitution_principles, _cross_artifact
from sddgrade.model import Artifact, ArtifactType


def _constitution(text: str) -> Artifact:
    return Artifact(
        path=".specify/memory/constitution.md",
        type=ArtifactType.CONSTITUTION,
        feature_id=None,
        raw=text,
        sections=parse_sections(text),
    )


def _plan(text: str, feature_id: str = "f1") -> Artifact:
    return Artifact(
        path=f"specs/{feature_id}/plan.md",
        type=ArtifactType.PLAN,
        feature_id=feature_id,
        raw=text,
        sections=parse_sections(text),
    )


_REAL_CONSTITUTION = """\
# Project Constitution

## Core Principles

### Library-First

Every feature begins as a self-contained module.

### Test-First

Tests precede implementation.

### Simplicity

Prefer the standard library.

## Governance

Amendments require two maintainers.
"""

_PLACEHOLDER_CONSTITUTION = """\
# [PROJECT_NAME] Constitution

## Core Principles

### [PRINCIPLE_1_NAME]

[PRINCIPLE_1_DESCRIPTION]

### [PRINCIPLE_2_NAME]

[PRINCIPLE_2_DESCRIPTION]

## Governance

[GOVERNANCE_RULES]
"""


def _pitfall_ids(findings) -> set[str]:
    return {f.pitfall_id for f in findings}


# ---------------------------------------------------------------------------
# _constitution_principles() helper


def test_principles_extracted_from_real_constitution():
    const = _constitution(_REAL_CONSTITUTION)
    principles = _constitution_principles(const)
    assert "Library-First" in principles
    assert "Test-First" in principles
    assert "Simplicity" in principles


def test_generic_headings_excluded():
    const = _constitution(_REAL_CONSTITUTION)
    principles = _constitution_principles(const)
    # Structural headings must not be returned
    assert "Core Principles" not in principles
    assert "Governance" not in principles


def test_placeholder_principles_excluded():
    const = _constitution(_PLACEHOLDER_CONSTITUTION)
    principles = _constitution_principles(const)
    assert principles == [], f"Expected empty list, got {principles}"


def test_empty_constitution_returns_no_principles():
    const = _constitution("# Empty\n\nNo headings.\n")
    assert _constitution_principles(const) == []


# ---------------------------------------------------------------------------
# Cross-artifact check via _cross_artifact()


def _run(artifacts, catalog=None):
    if catalog is None:
        catalog = load_catalog()
    return _cross_artifact(artifacts, catalog)


def test_no_constitution_skips_check():
    """No constitution artifact → SPECKIT-CONSTITUTION-CROSSCHECK must not fire."""
    plan_art = _plan(
        "# Plan\n\n## Summary\n\nOK.\n\n"
        "## Constitution Check\n\nPASS.\n"
    )
    # No constitution in the list
    findings = _run([plan_art])
    assert "SPECKIT-CONSTITUTION-CROSSCHECK" not in _pitfall_ids(findings)


def test_plan_references_principle_passes():
    """Constitution Check mentions a real principle name → no finding."""
    const = _constitution(_REAL_CONSTITUTION)
    plan_art = _plan(
        "# Plan\n\n## Summary\n\nOK.\n\n"
        "## Constitution Check\n\n"
        "- Simplicity: PASS — one project, no new services.\n"
        "- Test-First: PASS — tests precede implementation.\n\n"
        "Result: PASS. No violations.\n"
    )
    findings = _run([const, plan_art])
    assert "SPECKIT-CONSTITUTION-CROSSCHECK" not in _pitfall_ids(findings)


def test_plan_no_principle_reference_fires():
    """Constitution Check is generic boilerplate with no principle names → finding fires."""
    const = _constitution(_REAL_CONSTITUTION)
    plan_art = _plan(
        "# Plan\n\n## Summary\n\nOK.\n\n"
        "## Constitution Check\n\n"
        "PASS — no violations found.\n"
    )
    findings = _run([const, plan_art])
    assert "SPECKIT-CONSTITUTION-CROSSCHECK" in _pitfall_ids(findings)


def test_placeholder_constitution_skips_check():
    """All constitution principles are placeholders → no principles extracted → check skipped."""
    const = _constitution(_PLACEHOLDER_CONSTITUTION)
    plan_art = _plan(
        "# Plan\n\n## Summary\n\nOK.\n\n"
        "## Constitution Check\n\n"
        "PASS — no violations.\n"
    )
    findings = _run([const, plan_art])
    assert "SPECKIT-CONSTITUTION-CROSSCHECK" not in _pitfall_ids(findings)


def test_case_insensitive_principle_match():
    """Principle name check is case-insensitive."""
    const = _constitution(_REAL_CONSTITUTION)
    plan_art = _plan(
        "# Plan\n\n## Summary\n\nOK.\n\n"
        "## Constitution Check\n\n"
        "- library-first: PASS\n"  # lowercase version of "Library-First"
    )
    findings = _run([const, plan_art])
    assert "SPECKIT-CONSTITUTION-CROSSCHECK" not in _pitfall_ids(findings)


def test_no_constitution_check_section_skips_crosscheck():
    """Plan with no Constitution Check section → crosscheck skipped (PLAN-CONSTITUTION-UNCHECKED handles it)."""
    const = _constitution(_REAL_CONSTITUTION)
    plan_art = _plan(
        "# Plan\n\n## Summary\n\nOK.\n\n"
        "## Technical Context\n\nPython 3.11.\n"
    )
    findings = _run([const, plan_art])
    assert "SPECKIT-CONSTITUTION-CROSSCHECK" not in _pitfall_ids(findings)


def test_empty_constitution_check_body_skips_crosscheck():
    """Constitution Check section exists but body is empty → crosscheck skipped."""
    const = _constitution(_REAL_CONSTITUTION)
    plan_art = _plan(
        "# Plan\n\n## Summary\n\nOK.\n\n"
        "## Constitution Check\n\n"
    )
    findings = _run([const, plan_art])
    assert "SPECKIT-CONSTITUTION-CROSSCHECK" not in _pitfall_ids(findings)


def test_finding_points_to_plan_path():
    """The finding's artifact_path must reference the plan, not the constitution."""
    const = _constitution(_REAL_CONSTITUTION)
    plan_art = _plan(
        "# Plan\n\n## Summary\n\nOK.\n\n"
        "## Constitution Check\n\nPASS. No violations.\n",
        feature_id="feature-abc",
    )
    findings = _run([const, plan_art])
    crosscheck = [f for f in findings if f.pitfall_id == "SPECKIT-CONSTITUTION-CROSSCHECK"]
    assert len(crosscheck) == 1
    assert "plan.md" in crosscheck[0].artifact_path
