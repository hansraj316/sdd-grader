"""Tests for SPEC-GHERKIN-SCENARIO-OUTLINE-NO-EXAMPLES pitfall.

Rule: a Gherkin Scenario Outline (or Scenario Template) block must be followed
by an Examples: (or Scenarios:) section with at least one data row.  Without
the Examples table the outline is never instantiated — no test runs.

Guard: formal-Gherkin mode required (at least one When AND one Then line-leader
anywhere in the document).
Block boundaries: a new Scenario/Scenario Outline heading, or 2+ consecutive
blank lines.
"""
from __future__ import annotations

import textwrap

from sddgrade.adapters.base import parse_sections
from sddgrade.catalog import load_catalog
from sddgrade.engine.lint import _spec_gherkin_scenario_outline_no_examples
from sddgrade.model import Artifact, ArtifactType

CATALOG = load_catalog()
PITFALL = "SPEC-GHERKIN-SCENARIO-OUTLINE-NO-EXAMPLES"


def _spec(raw: str) -> Artifact:
    raw = textwrap.dedent(raw).strip()
    return Artifact(
        path="spec.md",
        type=ArtifactType.SPEC,
        feature_id="test",
        raw=raw,
        sections=parse_sections(raw),
    )


def _ids(art: Artifact) -> list[str]:
    return [f.pitfall_id for f in _spec_gherkin_scenario_outline_no_examples(art, CATALOG)]


def _fires(art: Artifact) -> bool:
    return PITFALL in _ids(art)


# ---------------------------------------------------------------------------
# Cases that FIRE
# ---------------------------------------------------------------------------


def test_outline_no_examples_fires():
    """Scenario Outline with no Examples table — must fire."""
    art = _spec("""
        ## Acceptance Criteria

        Scenario Outline: user logs in as <role>
          Given the user has <role> credentials
          When the user submits the login form
          Then the user sees the <role> dashboard
    """)
    assert _fires(art), "Expected SPEC-GHERKIN-SCENARIO-OUTLINE-NO-EXAMPLES to fire"


def test_outline_template_no_examples_fires():
    """Scenario Template variant with no Examples — must fire."""
    art = _spec("""
        ## Acceptance Criteria

        Scenario Template: uploading <size> file
          Given I am on the upload page
          When I upload a <size> file
          Then the system accepts the file
    """)
    assert _fires(art), "Expected fire for Scenario Template without Examples"


def test_multiple_outlines_one_missing_fires():
    """Two outlines; first has Examples, second does not — must fire."""
    art = _spec("""
        ## Acceptance Criteria

        Scenario Outline: login with <role>
          Given I am a <role>
          When I log in
          Then I see the dashboard
          Examples:
            | role  |
            | admin |

        Scenario Outline: logout with <role>
          Given I am a <role>
          When I log out
          Then I am redirected to login
    """)
    assert _fires(art), "Expected fire because second outline has no Examples"


def test_outline_with_markdown_heading_no_examples_fires():
    """Scenario Outline with ### heading prefix, no Examples — must fire."""
    art = _spec("""
        ## Acceptance Criteria

        ### Scenario Outline: bulk import with <format>
          Given a <format> file is ready
          When the user triggers import
          Then the system processes all rows
    """)
    assert _fires(art), "Expected fire for Scenario Outline with heading prefix"


def test_outline_closed_by_plain_scenario_fires():
    """Scenario Outline immediately followed by plain Scenario (no Examples) — must fire."""
    art = _spec("""
        ## Acceptance Criteria

        Scenario Outline: search by <type>
          Given the search is available
          When I search by <type>
          Then results are returned

        Scenario: basic sanity
          Given the system is running
          When I open the home page
          Then the page loads
    """)
    assert _fires(art), "Expected fire: Scenario Outline closed by plain Scenario with no Examples"


def test_outline_closed_by_two_blank_lines_fires():
    """Scenario Outline closed by 2+ blank lines before next Scenario — must fire."""
    art = _spec("""
        ## Acceptance Criteria

        Scenario Outline: search by <type>
          Given the search is available
          When I search by <type>
          Then results are returned


        Scenario: basic sanity
          Given the system is running
          When I open the home page
          Then the page loads
    """)
    assert _fires(art), "Expected fire: blank-line boundary closes outline block with no Examples"


# ---------------------------------------------------------------------------
# Cases that are SILENT
# ---------------------------------------------------------------------------


def test_outline_with_examples_silent():
    """Scenario Outline with Examples table — must be silent."""
    art = _spec("""
        ## Acceptance Criteria

        Scenario Outline: user logs in as <role>
          Given the user has <role> credentials
          When the user submits the login form
          Then the user sees the <role> dashboard
          Examples:
            | role  |
            | admin |
            | user  |
    """)
    assert not _fires(art), "Expected SILENT: Scenario Outline has Examples"


def test_outline_with_scenarios_keyword_silent():
    """Scenario Outline using Behave's 'Scenarios:' keyword — must be silent."""
    art = _spec("""
        ## Acceptance Criteria

        Scenario Outline: export <format>
          Given I have data
          When I export as <format>
          Then the file is downloaded
          Scenarios:
            | format |
            | csv    |
            | json   |
    """)
    assert not _fires(art), "Expected SILENT: 'Scenarios:' keyword satisfies Examples requirement"


def test_plain_scenario_no_outline_silent():
    """Plain Scenario (not Outline) — check must not fire."""
    art = _spec("""
        ## Acceptance Criteria

        Scenario: user logs in successfully
          Given the user has valid credentials
          When the user submits the login form
          Then the user sees the dashboard
    """)
    assert not _fires(art), "Expected SILENT: plain Scenario has no Examples requirement"


def test_no_formal_gherkin_guard_silent():
    """No When/Then line-leaders in document — guard suppresses the check."""
    art = _spec("""
        ## Acceptance Criteria

        Scenario Outline: user logs in as <role>
          The system authenticates the user as <role>.
    """)
    assert not _fires(art), "Expected SILENT: no formal Gherkin (no When/Then) — guard fires"


def test_fenced_outline_no_examples_silent():
    """Scenario Outline inside a fenced code block — must be silent."""
    art = _spec("""
        ## Example

        ```gherkin
        Scenario Outline: user logs in as <role>
          Given the user has <role> credentials
          When the user submits the login form
          Then the user sees the <role> dashboard
        ```

        ## Real Acceptance Criteria

        Scenario: basic login
          Given the user has valid credentials
          When the user logs in
          Then the dashboard is shown
    """)
    assert not _fires(art), "Expected SILENT: outline is inside fenced code block"


def test_multiple_outlines_all_with_examples_silent():
    """Two outlines both with Examples — must be completely silent."""
    art = _spec("""
        ## Acceptance Criteria

        Scenario Outline: login with <role>
          Given I am a <role>
          When I log in
          Then I see the dashboard
          Examples:
            | role  |
            | admin |

        Scenario Outline: logout with <role>
          Given I am a <role>
          When I log out
          Then I am on the login page
          Examples:
            | role |
            | user |
    """)
    assert not _fires(art), "Expected SILENT: both outlines have Examples"


def test_plan_artifact_silent():
    """Plan artifact — check must not fire (spec-only)."""
    raw = textwrap.dedent("""
        ## Deployment

        Scenario Outline: deploy <env>
          Given the build is green
          When deploy to <env>
          Then the service is up
    """).strip()
    art = Artifact(
        path="plan.md",
        type=ArtifactType.PLAN,
        feature_id="test",
        raw=raw,
        sections=parse_sections(raw),
    )
    assert not _fires(art), "Expected SILENT: plan artifact is not in scope"
