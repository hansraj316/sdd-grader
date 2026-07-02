"""EARS pattern check (#6) and ISO-29148 judge guidance (#7)."""

from __future__ import annotations

from sddgrade.adapters.base import parse_sections
from sddgrade.catalog import load_catalog
from sddgrade.engine.judge import build_prompt, judge_guidance
from sddgrade.engine.lint import _ears_pattern
from sddgrade.model import Artifact, ArtifactType


def _spec(text: str) -> Artifact:
    return Artifact(path="spec.md", type=ArtifactType.SPEC, feature_id="x",
                    raw=text, sections=parse_sections(text))


# ---- #6 EARS ----

def test_ears_flags_non_ears_shall():
    art = _spec("# S\n\n- Tasks shall be exportable.\n")  # no 'the <subj> shall', no keyword
    findings = _ears_pattern(art, load_catalog())
    assert len(findings) == 1
    assert findings[0].pitfall_id == "REQ-EARS-PATTERN"
    assert findings[0].severity.value == "info"  # advisory: never changes the score


def test_ears_clean_on_ubiquitous_and_keyword():
    ub = _spec("# S\n\n- FR-001: The system shall export tasks.\n")
    kw = _spec("# S\n\n- When the user clicks export, the system shall produce a CSV.\n")
    assert _ears_pattern(ub, load_catalog()) == []
    assert _ears_pattern(kw, load_catalog()) == []


def test_ears_is_zero_penalty():
    # info severity => zero penalty => cannot lower a score.
    art = _spec("# S\n\n- Tasks shall be exportable.\n")
    f = _ears_pattern(art, load_catalog())[0]
    assert f.severity.penalty == 0.0


# ---- #7 ISO-29148 judge ----

def test_29148_pitfall_in_catalog_and_judge_only():
    p = load_catalog()["JUDGE-29148-PERREQ"]
    assert p.method == "judge"
    assert p.judge_detectable and not p.lint_detectable


def test_judge_prompt_mentions_per_requirement_29148():
    prompt = build_prompt([_spec("# S\n\n- FR-001: The system shall export tasks.\n")])
    assert "29148" in prompt
    assert "JUDGE-29148-PERREQ" in prompt
    # And the catalog guidance includes it too.
    assert "JUDGE-29148-PERREQ" in judge_guidance()
