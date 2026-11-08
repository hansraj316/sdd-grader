"""Tests for SPEC-GHERKIN-GIVEN-ACTIVE-ACTION pitfall.

The check fires when a Gherkin Given step (or And/But that continues a Given)
contains a user-action verb (clicks, presses, submits, enters, types, fills,
selects, navigates, uploads, drags). One finding per offending line.

Guard: formal-Gherkin mode — both When and Then must be present in the doc.
"""

from __future__ import annotations

import pytest

from sddgrade.adapters.base import parse_sections
from sddgrade.catalog import load_catalog
from sddgrade.engine.lint import _spec_gherkin_given_active_action
from sddgrade.model import Artifact, ArtifactType


def _make_spec(raw: str) -> Artifact:
    return Artifact(
        path="spec.md",
        type=ArtifactType.SPEC,
        raw=raw,
        sections=parse_sections(raw),
    )


CATALOG = load_catalog()

_GHERKIN_FOOTER = "\nWhen the user submits\nThen the page refreshes\n"


# ---------------------------------------------------------------------------
# FIRE cases — check should trigger
# ---------------------------------------------------------------------------


def test_given_clicks_fires() -> None:
    """Given step with 'clicks' verb → fires."""
    spec = _make_spec(
        "# Spec\n\n"
        "## Acceptance\n\n"
        "Scenario: submit form\n"
        "  Given the user clicks the Submit button\n"
        "  When the form is validated\n"
        "  Then the confirmation page is shown\n"
    )
    findings = _spec_gherkin_given_active_action(spec, CATALOG)
    assert len(findings) == 1
    assert findings[0].pitfall_id == "SPEC-GHERKIN-GIVEN-ACTIVE-ACTION"
    assert findings[0].line == 6


def test_given_submits_fires() -> None:
    """Given step with 'submits' verb → fires."""
    spec = _make_spec(
        "# Spec\n\n"
        "Scenario: login\n"
        "  Given the user submits the login form\n"
        "  When credentials are checked\n"
        "  Then the dashboard is shown\n"
    )
    findings = _spec_gherkin_given_active_action(spec, CATALOG)
    assert len(findings) == 1
    assert findings[0].pitfall_id == "SPEC-GHERKIN-GIVEN-ACTIVE-ACTION"
    assert findings[0].line == 4


def test_given_enters_fires() -> None:
    """Given step with 'enters' verb → fires."""
    spec = _make_spec(
        "# Spec\n\n"
        "Scenario: search\n"
        "  Given the user enters a search term\n"
        "  When the search is executed\n"
        "  Then results are displayed\n"
    )
    findings = _spec_gherkin_given_active_action(spec, CATALOG)
    assert len(findings) == 1
    assert findings[0].line == 4


def test_and_continuation_of_given_fires() -> None:
    """And step continuing a Given that contains an action verb → fires."""
    spec = _make_spec(
        "# Spec\n\n"
        "Scenario: multi-step setup\n"
        "  Given the user is on the homepage\n"
        "  And the user clicks the Login link\n"
        "  When the login modal opens\n"
        "  Then the credentials form is visible\n"
    )
    findings = _spec_gherkin_given_active_action(spec, CATALOG)
    assert len(findings) == 1
    assert findings[0].pitfall_id == "SPEC-GHERKIN-GIVEN-ACTIVE-ACTION"
    assert findings[0].line == 5


def test_multiple_offending_given_lines_fires_each() -> None:
    """Two separate Given action-verb lines → two findings."""
    spec = _make_spec(
        "# Spec\n\n"
        "Scenario: upload\n"
        "  Given the user navigates to the upload page\n"
        "  Given the user selects a file\n"
        "  When the upload starts\n"
        "  Then progress is shown\n"
    )
    findings = _spec_gherkin_given_active_action(spec, CATALOG)
    assert len(findings) == 2


def test_given_types_fires() -> None:
    """Given step with 'types' verb → fires."""
    spec = _make_spec(
        "# Spec\n\n"
        "Scenario: search input\n"
        "  Given the user types 'hello' in the search box\n"
        "  When the search button is pressed\n"
        "  Then results appear\n"
    )
    findings = _spec_gherkin_given_active_action(spec, CATALOG)
    assert len(findings) == 1


def test_given_uploads_fires() -> None:
    """Given step with 'uploads' verb → fires."""
    spec = _make_spec(
        "# Spec\n\n"
        "Scenario: file upload\n"
        "  Given the user uploads an avatar image\n"
        "  When the form is submitted\n"
        "  Then the profile is updated\n"
    )
    findings = _spec_gherkin_given_active_action(spec, CATALOG)
    assert len(findings) == 1


# ---------------------------------------------------------------------------
# SILENT cases — check must NOT fire
# ---------------------------------------------------------------------------


def test_given_state_description_silent() -> None:
    """Given step that is a pure state description → silent."""
    spec = _make_spec(
        "# Spec\n\n"
        "Scenario: logged-in user\n"
        "  Given the user is logged in\n"
        "  When the user visits the dashboard\n"
        "  Then the welcome banner is shown\n"
    )
    findings = _spec_gherkin_given_active_action(spec, CATALOG)
    assert findings == []


def test_no_formal_gherkin_silent() -> None:
    """No formal-Gherkin mode (no When+Then) → silent."""
    spec = _make_spec(
        "# Spec\n\n"
        "## Acceptance\n\n"
        "Given the user clicks the button\n"
    )
    findings = _spec_gherkin_given_active_action(spec, CATALOG)
    assert findings == []


def test_fenced_given_action_silent() -> None:
    """Action-verb Given inside fenced code block → silent."""
    spec = _make_spec(
        "# Spec\n\n"
        "```gherkin\n"
        "Given the user clicks the button\n"
        "When the form validates\n"
        "Then success is shown\n"
        "```\n"
        "\n"
        "When the user logs in\n"
        "Then access is granted\n"
    )
    findings = _spec_gherkin_given_active_action(spec, CATALOG)
    assert findings == []


def test_when_step_with_action_verb_silent() -> None:
    """Action verb in a When step (not Given) → silent."""
    spec = _make_spec(
        "# Spec\n\n"
        "Scenario: form submission\n"
        "  Given the checkout page is displayed\n"
        "  When the user clicks Submit\n"
        "  Then the order is confirmed\n"
    )
    findings = _spec_gherkin_given_active_action(spec, CATALOG)
    assert findings == []


def test_and_after_when_with_action_verb_silent() -> None:
    """And step continuing a When (not Given) with action verb → silent."""
    spec = _make_spec(
        "# Spec\n\n"
        "Scenario: multi-action\n"
        "  Given the user is logged in\n"
        "  When the user opens the settings page\n"
        "  And the user clicks Save\n"
        "  Then the settings are stored\n"
    )
    findings = _spec_gherkin_given_active_action(spec, CATALOG)
    assert findings == []


def test_given_contains_word_select_as_noun_silent() -> None:
    """'select' used as noun in Given state description → silent (regex is verb-focused)."""
    spec = _make_spec(
        "# Spec\n\n"
        "Scenario: dropdown\n"
        "  Given the dropdown menu is visible\n"
        "  When the user chooses an option\n"
        "  Then the selection is applied\n"
    )
    findings = _spec_gherkin_given_active_action(spec, CATALOG)
    assert findings == []
