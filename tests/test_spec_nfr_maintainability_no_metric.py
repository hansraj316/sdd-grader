"""Tests for SPEC-NFR-MAINTAINABILITY-NO-METRIC pitfall check.

Fires when a normative requirement asserts maintainability/code quality/
technical debt without a measurable metric (ISO/IEC 25010:2023 Maintainability;
ISO 29148 §5.2.5(i); Volere Canon; MAQA completeness).
"""
from __future__ import annotations

import textwrap

from sddgrade.adapters.base import parse_sections
from sddgrade.catalog import load_catalog
from sddgrade.engine.lint import _spec_nfr_maintainability_no_metric
from sddgrade.model import Artifact, ArtifactType

CATALOG = load_catalog()
PITFALL = "SPEC-NFR-MAINTAINABILITY-NO-METRIC"


def _spec(raw: str) -> Artifact:
    raw = textwrap.dedent(raw).strip()
    return Artifact(
        path="spec.md",
        type=ArtifactType.SPEC,
        feature_id="test",
        raw=raw,
        sections=parse_sections(raw),
    )


def _plan(raw: str) -> Artifact:
    raw = textwrap.dedent(raw).strip()
    return Artifact(
        path="plan.md",
        type=ArtifactType.PLAN,
        feature_id="test",
        raw=raw,
        sections=parse_sections(raw),
    )


def _ids(art: Artifact) -> list[str]:
    return [f.pitfall_id for f in _spec_nfr_maintainability_no_metric(art, CATALOG)]


# ---------------------------------------------------------------------------
# FIRE cases — maintainability keyword with no measurable metric
# ---------------------------------------------------------------------------

def test_fire_bare_maintainable():
    """'maintainable' with no metric fires."""
    art = _spec("""
        ## Requirements

        - NFR-001: The system shall be maintainable.
    """)
    assert PITFALL in _ids(art)


def test_fire_bare_maintainability():
    """'maintainability' with no metric fires."""
    art = _spec("""
        ## Requirements

        - NFR-002: The system shall achieve high maintainability.
    """)
    assert PITFALL in _ids(art)


def test_fire_code_quality_no_metric():
    """'code quality' with no numeric metric fires."""
    art = _spec("""
        ## Requirements

        - NFR-003: The system shall maintain high code quality throughout development.
    """)
    assert PITFALL in _ids(art)


def test_fire_technical_debt_no_metric():
    """'technical debt' with no ratio/metric fires."""
    art = _spec("""
        ## Requirements

        - NFR-004: The team shall manage technical debt continuously.
    """)
    assert PITFALL in _ids(art)


def test_fire_codebase_quality_no_metric():
    """'codebase quality' with no metric fires."""
    art = _spec("""
        ## Requirements

        - NFR-005: The codebase quality shall be maintained over the project lifecycle.
    """)
    assert PITFALL in _ids(art)


def test_fire_multiple_lines():
    """Multiple offending lines each produce a finding."""
    art = _spec("""
        ## Requirements

        - NFR-006: The system shall be maintainable.
        - NFR-007: The system shall maintain good code quality.
    """)
    ids = _ids(art)
    assert ids.count(PITFALL) == 2


# ---------------------------------------------------------------------------
# SILENT cases — maintainability keyword WITH a measurable metric
# ---------------------------------------------------------------------------

def test_silent_coverage_percent():
    """'maintainability' with test coverage percentage silences."""
    art = _spec("""
        ## Requirements

        - NFR-008: The system shall be maintainable with test coverage >= 80%.
    """)
    assert PITFALL not in _ids(art)


def test_silent_cyclomatic_complexity():
    """'maintainable' with cyclomatic complexity silences."""
    art = _spec("""
        ## Requirements

        - NFR-009: The codebase shall be maintainable; no module shall exceed cyclomatic complexity of 10.
    """)
    assert PITFALL not in _ids(art)


def test_silent_debt_ratio():
    """'technical debt' with 'debt ratio' silences."""
    art = _spec("""
        ## Requirements

        - NFR-010: The technical debt ratio shall remain below 5% as measured by SonarQube.
    """)
    assert PITFALL not in _ids(art)


def test_silent_defect_density():
    """'code quality' with defect density metric silences."""
    art = _spec("""
        ## Requirements

        - NFR-011: Code quality shall be tracked via defect density metrics.
    """)
    assert PITFALL not in _ids(art)


def test_silent_non_requirement_line():
    """Maintainability mention in prose (no shall/must) does not fire."""
    art = _spec("""
        ## Background

        Good maintainability is a key goal of this project.

        ## Requirements

        - NFR-001: The system shall respond within 200ms.
    """)
    assert PITFALL not in _ids(art)


def test_silent_fenced_block():
    """Maintainability keyword in fenced block does not fire."""
    art = _spec("""
        ## Requirements

        ```
        - NFR-001: The system shall be maintainable.
        ```
    """)
    assert PITFALL not in _ids(art)


def test_silent_plan_artifact():
    """Plan artifact is not checked (spec-only)."""
    art = _plan("""
        ## Plan

        - NFR-001: The system shall be maintainable.
    """)
    assert PITFALL not in _ids(art)


def test_silent_coupling_metric():
    """'maintainability' with coupling metric silences."""
    art = _spec("""
        ## Requirements

        - NFR-012: The system shall achieve maintainability by keeping module coupling below 0.3.
    """)
    assert PITFALL not in _ids(art)
