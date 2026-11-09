"""Tests for SPEC-GHERKIN-THEN-MULTIPLE-ASSERTIONS pitfall.

The check fires when a Gherkin scenario block contains 3+ Then assertion lines
(Then steps plus And/But continuations in Then-context). One finding per offending
block, anchored at the 3rd assertion line.

Guard: formal-Gherkin mode — both When and Then must be present in the doc.
"""

from __future__ import annotations

import pytest

from sddgrade.adapters.base import parse_sections
from sddgrade.catalog import load_catalog
from sddgrade.engine.lint import _spec_gherkin_then_multiple_assertions
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


def test_three_then_steps_fires() -> None:
    """Scenario with 3 separate Then steps → fires."""
    spec = _make_spec(
        "# Spec\n\n"
        "Scenario: multi-assert\n"
        "  Given the user is logged in\n"
        "  When the user visits the dashboard\n"
        "  Then the page title is correct\n"
        "  Then the welcome message is shown\n"
        "  Then the logout button is visible\n"
    )
    findings = _spec_gherkin_then_multiple_assertions(spec, CATALOG)
    assert len(findings) == 1
    assert findings[0].pitfall_id == "SPEC-GHERKIN-THEN-MULTIPLE-ASSERTIONS"
    assert findings[0].line == 8  # 3rd Then line


def test_then_and_continuation_fires() -> None:
    """Then + 2 And continuations (all in Then-context) → fires."""
    spec = _make_spec(
        "# Spec\n\n"
        "Scenario: form submission\n"
        "  Given the checkout form is displayed\n"
        "  When the user clicks Submit\n"
        "  Then the order is created\n"
        "  And the confirmation email is sent\n"
        "  And the inventory is decremented\n"
    )
    findings = _spec_gherkin_then_multiple_assertions(spec, CATALOG)
    assert len(findings) == 1
    assert findings[0].pitfall_id == "SPEC-GHERKIN-THEN-MULTIPLE-ASSERTIONS"
    assert findings[0].line == 8  # 3rd assertion (2nd And)


def test_mixed_then_and_fires() -> None:
    """Then + And + Then → 3 assertions → fires."""
    spec = _make_spec(
        "# Spec\n\n"
        "Scenario: profile update\n"
        "  Given the user is on the profile page\n"
        "  When the user clicks Save\n"
        "  Then the profile is updated\n"
        "  And the success toast is shown\n"
        "  Then the page reloads\n"
    )
    findings = _spec_gherkin_then_multiple_assertions(spec, CATALOG)
    assert len(findings) == 1
    assert findings[0].line == 8  # 3rd assertion


def test_four_assertions_fires_once() -> None:
    """4 assertion lines in one block → fires exactly once."""
    spec = _make_spec(
        "# Spec\n\n"
        "Scenario: admin dashboard\n"
        "  Given the admin is logged in\n"
        "  When the admin opens the dashboard\n"
        "  Then the user count is shown\n"
        "  And the revenue chart is shown\n"
        "  And the error log is shown\n"
        "  And the recent activity is shown\n"
    )
    findings = _spec_gherkin_then_multiple_assertions(spec, CATALOG)
    assert len(findings) == 1


def test_two_scenarios_both_offending_fires_twice() -> None:
    """Two scenario blocks each with 3+ assertions → two findings."""
    spec = _make_spec(
        "# Spec\n\n"
        "Scenario: first\n"
        "  Given state A\n"
        "  When action A\n"
        "  Then result A1\n"
        "  And result A2\n"
        "  And result A3\n"
        "\n"
        "Scenario: second\n"
        "  Given state B\n"
        "  When action B\n"
        "  Then result B1\n"
        "  And result B2\n"
        "  And result B3\n"
    )
    findings = _spec_gherkin_then_multiple_assertions(spec, CATALOG)
    assert len(findings) == 2


# ---------------------------------------------------------------------------
# SILENT cases — check must NOT fire
# ---------------------------------------------------------------------------


def test_two_assertions_silent() -> None:
    """Exactly 2 Then/And assertion lines → silent (threshold is 3)."""
    spec = _make_spec(
        "# Spec\n\n"
        "Scenario: login\n"
        "  Given the user is on the login page\n"
        "  When the user submits valid credentials\n"
        "  Then the dashboard is shown\n"
        "  And the welcome banner is displayed\n"
    )
    findings = _spec_gherkin_then_multiple_assertions(spec, CATALOG)
    assert findings == []


def test_one_then_silent() -> None:
    """Single Then step → silent."""
    spec = _make_spec(
        "# Spec\n\n"
        "Scenario: simple\n"
        "  Given the page is loaded\n"
        "  When the user clicks OK\n"
        "  Then the dialog closes\n"
    )
    findings = _spec_gherkin_then_multiple_assertions(spec, CATALOG)
    assert findings == []


def test_no_formal_gherkin_silent() -> None:
    """No formal-Gherkin mode (no When+Then present) → silent."""
    spec = _make_spec(
        "# Spec\n\n"
        "## Acceptance\n\n"
        "Given the user is on the page\n"
        "Then result A\n"
        "Then result B\n"
        "Then result C\n"
    )
    findings = _spec_gherkin_then_multiple_assertions(spec, CATALOG)
    assert findings == []


def test_fenced_then_lines_silent() -> None:
    """Then lines inside a fenced code block → silent."""
    spec = _make_spec(
        "# Spec\n\n"
        "```gherkin\n"
        "Given state\n"
        "When action\n"
        "Then result A\n"
        "Then result B\n"
        "Then result C\n"
        "```\n"
        "\n"
        "When the user logs in\n"
        "Then access is granted\n"
    )
    findings = _spec_gherkin_then_multiple_assertions(spec, CATALOG)
    assert findings == []


def test_and_after_when_not_counted() -> None:
    """And steps after When (not Then) are NOT assertion lines → silent."""
    spec = _make_spec(
        "# Spec\n\n"
        "Scenario: multi-action\n"
        "  Given state\n"
        "  When the user opens the form\n"
        "  And the user fills in the name\n"
        "  And the user clicks Submit\n"
        "  Then the record is saved\n"
    )
    findings = _spec_gherkin_then_multiple_assertions(spec, CATALOG)
    assert findings == []


def test_separate_scenarios_each_two_assertions_silent() -> None:
    """Two scenarios each with exactly 2 assertions → silent (never reaches 3)."""
    spec = _make_spec(
        "# Spec\n\n"
        "Scenario: first\n"
        "  Given state A\n"
        "  When action A\n"
        "  Then result A1\n"
        "  And result A2\n"
        "\n"
        "Scenario: second\n"
        "  Given state B\n"
        "  When action B\n"
        "  Then result B1\n"
        "  And result B2\n"
    )
    findings = _spec_gherkin_then_multiple_assertions(spec, CATALOG)
    assert findings == []


def test_blank_line_reset_then_count_silent() -> None:
    """Two consecutive blank lines reset the scenario; each sub-block ≤2 assertions → silent."""
    spec = _make_spec(
        "# Spec\n\n"
        "Given state\n"
        "When action\n"
        "Then result A\n"
        "And result B\n"
        "\n\n"
        "Given another state\n"
        "When another action\n"
        "Then result C\n"
        "And result D\n"
        "\n\n"
        "When the user logs in\n"
        "Then access is granted\n"
    )
    findings = _spec_gherkin_then_multiple_assertions(spec, CATALOG)
    assert findings == []
