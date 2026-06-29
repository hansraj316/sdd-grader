"""Unit tests for the unclear-actor check (SPEC-UNCLEAR-ACTOR)."""

from __future__ import annotations

from sddreview.adapters.base import parse_sections
from sddreview.catalog import load_catalog
from sddreview.engine.lint import _unclear_actor
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


def _findings(art: Artifact) -> list:
    return _unclear_actor(art, load_catalog())


def test_pronoun_it_shall_fires():
    art = _spec("# Spec\n\n- FR-001: It shall display the confirmation dialog.\n")
    findings = _findings(art)
    assert len(findings) == 1
    assert findings[0].pitfall_id == "SPEC-UNCLEAR-ACTOR"


def test_pronoun_they_must_fires():
    art = _spec("# Spec\n\n- FR-002: They must respond within 200ms.\n")
    findings = _findings(art)
    assert len(findings) == 1
    assert findings[0].pitfall_id == "SPEC-UNCLEAR-ACTOR"


def test_pronoun_this_should_fires():
    art = _spec("# Spec\n\n- FR-003: This should validate the user input before submission.\n")
    findings = _findings(art)
    assert len(findings) == 1


def test_pronoun_that_shall_fires():
    art = _spec("# Spec\n\n- FR-001: That shall handle at most 1000 concurrent users.\n")
    findings = _findings(art)
    assert len(findings) == 1


def test_subjectless_requirement_fires():
    art = _spec("# Spec\n\n- FR-001: Shall generate a PDF report on demand.\n")
    findings = _findings(art)
    assert len(findings) == 1


def test_clear_system_actor_is_clean():
    art = _spec("# Spec\n\n- FR-001: The system shall export the user's tasks as a CSV.\n")
    assert _findings(art) == []


def test_named_component_actor_is_clean():
    art = _spec("# Spec\n\n- FR-001: The API gateway shall validate JWT tokens on every request.\n")
    assert _findings(art) == []


def test_multiple_pronoun_lines_single_finding():
    text = (
        "# Spec\n\n"
        "- FR-001: It shall log all errors to a centralised store.\n"
        "- FR-002: They must not cache responses longer than 60s.\n"
    )
    art = _spec(text)
    findings = _findings(art)
    assert len(findings) == 1
    assert "2 line" in findings[0].message


def test_applies_to_plan_artifact():
    art = _plan("# Plan\n\n- NFR-001: It should handle burst traffic without throttling.\n")
    findings = _findings(art)
    assert len(findings) == 1


def test_line_number_is_first_occurrence():
    text = (
        "# Spec\n"
        "\n"
        "- FR-001: It shall queue the request.\n"   # line 3
        "- FR-002: They must retry on failure.\n"   # line 4
    )
    art = _spec(text)
    findings = _findings(art)
    assert findings[0].line == 3
