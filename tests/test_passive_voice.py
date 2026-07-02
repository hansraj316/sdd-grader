"""Unit tests for the passive-voice requirement check (SPEC-PASSIVE-VOICE)."""

from __future__ import annotations

from sddgrade.adapters.base import parse_sections
from sddgrade.catalog import load_catalog
from sddgrade.engine.lint import _passive_voice
from sddgrade.model import Artifact, ArtifactType


def _spec(text: str) -> Artifact:
    return Artifact(
        path="spec.md", type=ArtifactType.SPEC, feature_id="x",
        raw=text, sections=parse_sections(text),
    )


def test_passive_voice_fires_on_passive_requirement():
    art = _spec("# Spec\n\n- FR-001: The data shall be validated by the service.\n")
    findings = _passive_voice(art, load_catalog())
    assert len(findings) == 1
    assert findings[0].pitfall_id == "SPEC-PASSIVE-VOICE"
    assert findings[0].suggestion


def test_active_voice_requirement_is_clean():
    art = _spec("# Spec\n\n- FR-001: The service shall validate all incoming data.\n")
    assert _passive_voice(art, load_catalog()) == []


def test_shall_be_able_not_flagged():
    """'shall be able to ...' is an active capability requirement, not passive voice."""
    art = _spec("# Spec\n\n- FR-001: The user shall be able to export tasks.\n")
    assert _passive_voice(art, load_catalog()) == []


def test_passive_to_be_form_fires():
    """'to be [past-participle]' on a requirement line is also passive voice."""
    art = _spec("# Spec\n\n- FR-001: The system shall allow data to be exported.\n")
    findings = _passive_voice(art, load_catalog())
    assert len(findings) == 1
    assert findings[0].pitfall_id == "SPEC-PASSIVE-VOICE"


def test_passive_in_prose_not_flagged():
    """Passive constructions in plain prose (no requirement marker) must not fire."""
    art = _spec("# Spec\n\nThe data is processed in batches for efficiency.\n")
    assert _passive_voice(art, load_catalog()) == []


def test_multiple_passive_requirements_single_finding():
    text = (
        "# Spec\n\n"
        "- FR-001: Users shall be authenticated by the gateway.\n"
        "- FR-002: Sessions shall be created upon login.\n"
    )
    art = _spec(text)
    findings = _passive_voice(art, load_catalog())
    assert len(findings) == 1
    assert "2 line(s)" in findings[0].message
