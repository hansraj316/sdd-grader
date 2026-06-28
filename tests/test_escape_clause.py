"""Unit tests for the escape-clause requirement check (SPEC-ESCAPE-CLAUSE)."""

from __future__ import annotations

from sddreview.adapters.base import parse_sections
from sddreview.catalog import load_catalog
from sddreview.engine.lint import _lexical_pitfalls
from sddreview.model import Artifact, ArtifactType


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


def _escape_findings(art: Artifact) -> list:
    return [f for f in _lexical_pitfalls(art, load_catalog()) if f.pitfall_id == "SPEC-ESCAPE-CLAUSE"]


def test_where_feasible_fires():
    art = _spec("# Spec\n\n- FR-001: The system shall encrypt data where feasible.\n")
    findings = _escape_findings(art)
    assert len(findings) == 1
    assert findings[0].pitfall_id == "SPEC-ESCAPE-CLAUSE"


def test_to_the_extent_practical_fires():
    art = _spec("# Spec\n\n- FR-002: Logs shall be retained to the extent practical.\n")
    findings = _escape_findings(art)
    assert len(findings) == 1


def test_best_effort_fires():
    art = _spec("# Spec\n\n- FR-003: The service shall deliver events on a best effort basis.\n")
    findings = _escape_findings(art)
    assert len(findings) == 1


def test_reasonable_effort_fires():
    art = _spec("# Spec\n\n- FR-004: The system shall make a reasonable effort to notify users.\n")
    findings = _escape_findings(art)
    assert len(findings) == 1


def test_if_applicable_fires():
    art = _spec("# Spec\n\n- FR-005: Authentication shall be enforced if applicable.\n")
    findings = _escape_findings(art)
    assert len(findings) == 1


def test_concrete_requirement_is_clean():
    art = _spec("# Spec\n\n- FR-001: The system shall encrypt all data at rest using AES-256.\n")
    assert _escape_findings(art) == []


def test_at_the_discretion_fires():
    art = _spec("# Spec\n\n- FR-006: Access may be revoked at the discretion of the admin.\n")
    findings = _escape_findings(art)
    assert len(findings) == 1


def test_applies_to_plan_artifact():
    art = _plan("# Plan\n\n- NFR-001: Performance targets shall be met where possible.\n")
    findings = _escape_findings(art)
    assert len(findings) == 1


def test_multiple_escape_clauses_single_finding():
    text = (
        "# Spec\n\n"
        "- FR-001: Data shall be encrypted where feasible.\n"
        "- FR-002: Logs shall be kept to the extent practical.\n"
    )
    art = _spec(text)
    findings = _escape_findings(art)
    assert len(findings) == 1
    assert "2 occurrence" in findings[0].message
