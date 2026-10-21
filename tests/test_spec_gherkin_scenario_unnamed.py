"""Tests for SPEC-GHERKIN-SCENARIO-UNNAMED pitfall."""
from __future__ import annotations

import textwrap

from sddgrade.adapters.base import parse_sections
from sddgrade.catalog import load_catalog
from sddgrade.engine.lint import _spec_gherkin_scenario_unnamed
from sddgrade.model import Artifact, ArtifactType

CATALOG = load_catalog()
PITFALL_ID = "SPEC-GHERKIN-SCENARIO-UNNAMED"


def _spec(raw: str) -> Artifact:
    raw = textwrap.dedent(raw).strip()
    return Artifact(
        path="spec.md",
        type=ArtifactType.SPEC,
        feature_id="test",
        raw=raw,
        sections=parse_sections(raw),
    )


def _findings(raw: str):
    art = _spec(raw)
    return _spec_gherkin_scenario_unnamed(art, CATALOG)


# ---------------------------------------------------------------------------
# Fire cases
# ---------------------------------------------------------------------------

def test_fire_bare_scenario():
    """Bare 'Scenario:' with no title → fires."""
    md = """\
    ## Acceptance Criteria

    Scenario:
      Given the user is on the login page
      When the user submits valid credentials
      Then the dashboard is displayed
    """
    assert _findings(md), "Should fire: Scenario: with no title"


def test_fire_bare_scenario_outline():
    """Bare 'Scenario Outline:' with no title → fires."""
    md = """\
    ## Acceptance Criteria

    Scenario Outline:
      Given the user has role <role>
      When the user accesses the admin panel
      Then the response matches <expected>
    """
    assert _findings(md), "Should fire: Scenario Outline: with no title"


def test_fire_bare_scenario_template():
    """Bare 'Scenario Template:' with no title → fires."""
    md = """\
    ## Acceptance Criteria

    Scenario Template:
      Given the system is running
      When the event fires
      Then the result is recorded
    """
    assert _findings(md), "Should fire: Scenario Template: with no title"


def test_fire_multiple_unnamed():
    """Multiple unnamed scenarios → fires (aggregate at first)."""
    md = """\
    ## Acceptance Criteria

    Scenario:
      Given state A
      When action B
      Then result C

    Scenario:
      Given state D
      When action E
      Then result F
    """
    findings = _findings(md)
    assert findings, "Should fire: multiple unnamed scenarios"
    assert findings[0].line == 3, "Should anchor at first unnamed scenario line"


def test_fire_unnamed_with_whitespace_only():
    """'Scenario:   ' (trailing whitespace only) → fires."""
    md = """\
    ## Acceptance Criteria

    Scenario:
      Given the user is logged in
      When the user requests logout
      Then the session is ended
    """
    assert _findings(md), "Should fire: Scenario: with only trailing whitespace"


def test_fire_heading_prefixed_unnamed():
    """'## Scenario:' with no title → fires."""
    md = """\
    ## Acceptance Criteria

    ## Scenario:
      Given precondition
      When action taken
      Then outcome occurs
    """
    assert _findings(md), "Should fire: ## Scenario: with no title"


# ---------------------------------------------------------------------------
# Silent cases
# ---------------------------------------------------------------------------

def test_silent_titled_scenario():
    """Scenario with a title → silent."""
    md = """\
    ## Acceptance Criteria

    Scenario: User logs in with valid credentials
      Given the user is on the login page
      When the user submits valid credentials
      Then the dashboard is displayed
    """
    assert not _findings(md), "Should be silent: scenario has a title"


def test_silent_titled_scenario_outline():
    """Scenario Outline with a title → silent."""
    md = """\
    ## Acceptance Criteria

    Scenario Outline: User login with <role>
      Given the user has role <role>
      When the user logs in
      Then access is <result>
    """
    assert not _findings(md), "Should be silent: scenario outline has a title"


def test_silent_no_formal_gherkin():
    """No When/Then line-leaders → formal-Gherkin guard fails → silent."""
    md = """\
    ## Acceptance Criteria

    Scenario:
      The system must handle edge cases gracefully.
    """
    assert not _findings(md), "Should be silent: no formal-Gherkin mode"


def test_silent_fenced_unnamed():
    """Unnamed Scenario: inside fenced block → excluded → silent."""
    md = """\
    ## Acceptance Criteria

    ```gherkin
    Scenario:
      Given precondition
      When action
      Then result
    ```

    When using Gherkin, always add a title after Scenario:.
    Then the test results will be identifiable.
    """
    assert not _findings(md), "Should be silent: unnamed scenario only in fenced block"


def test_silent_word_scenario_in_prose():
    """The word 'scenario' in prose with colon but not as keyword → silent."""
    md = """\
    ## Acceptance Criteria

    The following scenario: edge case handling must be addressed.

    When the user submits a form
    Then the response is returned within 200ms
    """
    assert not _findings(md), "Should be silent: 'scenario:' in prose is not a keyword line"
