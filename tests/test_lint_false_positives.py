"""Regression tests for lexical-pitfall false positives (issue #38).

Benign prose — trailing ellipses in lists, vague words in narrative, domain
technology terms, out-of-scope declarations, and anything inside code fences —
must NOT be flagged. The same tokens in genuine requirement contexts MUST still
be flagged.
"""

from __future__ import annotations

from sddgrade.adapters.base import parse_sections
from sddgrade.catalog import load_catalog
from sddgrade.engine.lint import _lexical_pitfalls
from sddgrade.model import Artifact, ArtifactType


def _spec(text: str) -> Artifact:
    return Artifact(
        path="spec.md", type=ArtifactType.SPEC, feature_id="x",
        raw=text, sections=parse_sections(text),
    )


def _ids(art: Artifact) -> set[str]:
    return {f.pitfall_id for f in _lexical_pitfalls(art, load_catalog()) if f.pitfall_id}


def _findings(art: Artifact, pitfall_id: str) -> list:
    return [
        f for f in _lexical_pitfalls(art, load_catalog()) if f.pitfall_id == pitfall_id
    ]


# ------------------------------------------------------- SPEC-LEFTOVER-PLACEHOLDER

def test_trailing_ellipsis_in_prose_list_is_not_a_placeholder():
    art = _spec(
        "# Feature Specification: Agent Support\n\n"
        "## Overview\n\n"
        "Supported agents: Claude, Copilot, Cursor, ...\n"
        "The wizard walks through steps 1, 2, 3...\n"
    )
    assert _findings(art, "SPEC-LEFTOVER-PLACEHOLDER") == []


def test_empty_field_ellipsis_is_still_a_placeholder():
    art = _spec(
        "# Feature Specification: Export\n\n"
        "## Requirements\n\n"
        "**Owner:** ...\n"
    )
    assert len(_findings(art, "SPEC-LEFTOVER-PLACEHOLDER")) == 1


def test_bare_ellipsis_line_is_still_a_placeholder():
    art = _spec("# Spec\n\n## Requirements\n\n- ...\n")
    assert len(_findings(art, "SPEC-LEFTOVER-PLACEHOLDER")) == 1


def test_todo_is_still_a_placeholder():
    art = _spec("# Spec\n\nTODO: write acceptance criteria.\n")
    assert len(_findings(art, "SPEC-LEFTOVER-PLACEHOLDER")) == 1


# -------------------------------------------------------- SPEC-AMBIGUOUS-WORDING

def test_ambiguous_words_in_narrative_prose_are_not_flagged():
    art = _spec(
        "# Feature Specification: Filters\n\n"
        "## User Scenarios & Testing\n\n"
        "### User Story 1 - Filter data (Priority: P1)\n\n"
        "The analyst selects some of the filters to narrow the view.\n"
        "A simple moving average smooths the chart.\n"
        "Works with common mail clients (Outlook, Gmail, etc.).\n"
    )
    assert _findings(art, "SPEC-AMBIGUOUS-WORDING") == []


def test_ambiguous_words_in_requirements_are_still_flagged():
    art = _spec(
        "# Spec\n\n"
        "## Requirements\n\n"
        "### Functional Requirements\n\n"
        "- FR-001: The system shall support some export formats, etc.\n"
    )
    assert len(_findings(art, "SPEC-AMBIGUOUS-WORDING")) == 1


def test_ambiguous_words_on_requirementish_line_outside_section_still_flagged():
    art = _spec("# Spec\n\nThe importer must be fast and robust.\n")
    assert len(_findings(art, "SPEC-AMBIGUOUS-WORDING")) == 1


# --------------------------------------------------------- SPEC-IMPL-DETAIL-LEAK

def test_domain_technology_is_not_an_impl_leak():
    art = _spec(
        "# Feature Specification: Python Project Reviewer\n\n"
        "## Overview\n\n"
        "The tool reviews Python projects and reports issues.\n\n"
        "## Requirements\n\n"
        "### Functional Requirements\n\n"
        "- FR-001: The tool shall parse Python source files.\n"
    )
    assert _findings(art, "SPEC-IMPL-DETAIL-LEAK") == []


def test_non_domain_technology_in_requirement_is_still_an_impl_leak():
    art = _spec(
        "# Feature Specification: Python Project Reviewer\n\n"
        "## Overview\n\n"
        "The tool reviews Python projects and reports issues.\n\n"
        "## Requirements\n\n"
        "### Functional Requirements\n\n"
        "- FR-001: The tool shall parse Python source files.\n"
        "- FR-002: Results shall be stored in Postgres.\n"
    )
    findings = _findings(art, "SPEC-IMPL-DETAIL-LEAK")
    assert len(findings) == 1
    assert "Postgres" in findings[0].message
    assert "Python" not in findings[0].message


def test_technology_in_narrative_prose_is_not_an_impl_leak():
    art = _spec(
        "# Feature Specification: Notifications\n\n"
        "## User Scenarios & Testing\n\n"
        "### User Story 1 - Receive alerts (Priority: P1)\n\n"
        "Today the team pastes alerts into Kafka topics by hand.\n"
    )
    assert _findings(art, "SPEC-IMPL-DETAIL-LEAK") == []


# ------------------------------------------------------ SPEC-SPECULATIVE-FEATURE

def test_eventually_in_out_of_scope_is_not_speculative():
    art = _spec(
        "# Feature Specification: Export\n\n"
        "## Out of Scope\n\n"
        "- Eventually we may want to support mobile push, but it is out of scope.\n"
    )
    assert _findings(art, "SPEC-SPECULATIVE-FEATURE") == []


def test_speculative_requirement_is_still_flagged():
    art = _spec(
        "# Spec\n\n"
        "## Requirements\n\n"
        "### Functional Requirements\n\n"
        "- FR-002: We might need a message queue in the future for scale.\n"
    )
    assert len(_findings(art, "SPEC-SPECULATIVE-FEATURE")) == 1


# --------------------------------------------------------------- code fences

def test_nothing_fires_inside_fenced_code_blocks():
    art = _spec(
        "# Spec\n\n"
        "## Requirements\n\n"
        "### Functional Requirements\n\n"
        "- FR-001: The system shall export CSV.\n\n"
        "```python\n"
        "# TODO: some simple placeholder, fast etc.\n"
        "client = React | Postgres  # might need this eventually ...\n"
        "```\n"
    )
    assert _ids(art) == set()


def test_inline_code_span_is_not_matched():
    art = _spec(
        "# Spec\n\n"
        "## Requirements\n\n"
        "### Functional Requirements\n\n"
        "- FR-001: The system shall expose the `npm` command name verbatim.\n"
    )
    assert _findings(art, "SPEC-IMPL-DETAIL-LEAK") == []
