"""Tests for SPEC-GHERKIN-THEN-IMPERATIVE pitfall.

The check fires when a Gherkin Then step (or And/But that continues a Then)
starts with an imperative user-action verb (click, navigate, press, fill,
submit, type, select, upload, drag, choose, open, close, tap, swipe, scroll,
enter, check, uncheck).  One finding per offending line.

Guard: formal-Gherkin mode — both When and Then must be present in the doc.
"""

from __future__ import annotations

import pytest

from sddgrade.adapters.base import parse_sections
from sddgrade.catalog import load_catalog
from sddgrade.engine.lint import _spec_gherkin_then_imperative
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


def test_then_click_fires() -> None:
    """Then clause starting with 'click' → fires."""
    spec = _make_spec(
        "# Spec\n\n"
        "Scenario: save record\n"
        "  Given the edit form is open\n"
        "  When the user modifies the title\n"
        "  Then click the Save button\n"
    )
    findings = _spec_gherkin_then_imperative(spec, CATALOG)
    assert len(findings) == 1
    assert findings[0].pitfall_id == "SPEC-GHERKIN-THEN-IMPERATIVE"
    assert findings[0].line == 6


def test_then_navigate_fires() -> None:
    """Then clause starting with 'navigate' → fires."""
    spec = _make_spec(
        "# Spec\n\n"
        "Scenario: redirect\n"
        "  Given the user is logged in\n"
        "  When the session expires\n"
        "  Then navigate to the login page\n"
    )
    findings = _spec_gherkin_then_imperative(spec, CATALOG)
    assert len(findings) == 1
    assert findings[0].pitfall_id == "SPEC-GHERKIN-THEN-IMPERATIVE"
    assert findings[0].line == 6


def test_then_submit_fires() -> None:
    """Then clause starting with 'submit' → fires."""
    spec = _make_spec(
        "# Spec\n\n"
        "Scenario: form flow\n"
        "  Given the form is filled\n"
        "  When the user reviews the data\n"
        "  Then submit the form\n"
    )
    findings = _spec_gherkin_then_imperative(spec, CATALOG)
    assert len(findings) == 1
    assert findings[0].line == 6


def test_and_in_then_context_fires() -> None:
    """And step continuing a Then that starts with 'click' → fires."""
    spec = _make_spec(
        "# Spec\n\n"
        "Scenario: multi-step outcome\n"
        "  Given the checkout page is loaded\n"
        "  When the user confirms the order\n"
        "  Then the order summary is shown\n"
        "  And click the Print Receipt button\n"
    )
    findings = _spec_gherkin_then_imperative(spec, CATALOG)
    assert len(findings) == 1
    assert findings[0].pitfall_id == "SPEC-GHERKIN-THEN-IMPERATIVE"
    assert findings[0].line == 7


def test_then_enter_fires() -> None:
    """Then clause starting with 'enter' → fires."""
    spec = _make_spec(
        "# Spec\n\n"
        "Scenario: pin entry\n"
        "  Given the payment screen is displayed\n"
        "  When the card is inserted\n"
        "  Then enter the PIN code\n"
    )
    findings = _spec_gherkin_then_imperative(spec, CATALOG)
    assert len(findings) == 1


def test_then_scroll_fires() -> None:
    """Then clause starting with 'scroll' → fires."""
    spec = _make_spec(
        "# Spec\n\n"
        "Scenario: load more\n"
        "  Given the feed is displayed\n"
        "  When the user reaches the end\n"
        "  Then scroll down to load more items\n"
    )
    findings = _spec_gherkin_then_imperative(spec, CATALOG)
    assert len(findings) == 1


def test_then_uncheck_fires() -> None:
    """Then clause starting with 'uncheck' → fires."""
    spec = _make_spec(
        "# Spec\n\n"
        "Scenario: toggle preference\n"
        "  Given the notification setting is enabled\n"
        "  When the user opens preferences\n"
        "  Then uncheck the email notification box\n"
    )
    findings = _spec_gherkin_then_imperative(spec, CATALOG)
    assert len(findings) == 1


def test_multiple_offending_then_lines_fires_each() -> None:
    """Two Then lines starting with action verbs → two findings."""
    spec = _make_spec(
        "# Spec\n\n"
        "Scenario: download flow\n"
        "  Given the file list is shown\n"
        "  When the user selects a file\n"
        "  Then click the Download button\n"
        "  And navigate to the downloads folder\n"
    )
    findings = _spec_gherkin_then_imperative(spec, CATALOG)
    assert len(findings) == 2


# ---------------------------------------------------------------------------
# SILENT cases — check must NOT fire
# ---------------------------------------------------------------------------


def test_then_observable_outcome_silent() -> None:
    """Then clause starting with 'the' (observable state) → silent."""
    spec = _make_spec(
        "# Spec\n\n"
        "Scenario: save success\n"
        "  Given the edit form is open\n"
        "  When the user clicks Save\n"
        "  Then the record is saved successfully\n"
    )
    findings = _spec_gherkin_then_imperative(spec, CATALOG)
    assert findings == []


def test_given_click_not_then_silent() -> None:
    """Action verb in a Given clause (not Then) → silent for this check."""
    spec = _make_spec(
        "# Spec\n\n"
        "Scenario: misplaced action\n"
        "  Given the user clicks the button\n"
        "  When the form validates\n"
        "  Then the success banner is shown\n"
    )
    findings = _spec_gherkin_then_imperative(spec, CATALOG)
    assert findings == []


def test_no_formal_gherkin_silent() -> None:
    """No formal-Gherkin mode (no When+Then) → silent."""
    spec = _make_spec(
        "# Spec\n\n"
        "## Acceptance\n\n"
        "Then click the Save button\n"
    )
    findings = _spec_gherkin_then_imperative(spec, CATALOG)
    assert findings == []


def test_fenced_then_imperative_silent() -> None:
    """Imperative Then inside fenced code block → silent."""
    spec = _make_spec(
        "# Spec\n\n"
        "```gherkin\n"
        "Given precondition\n"
        "When the user acts\n"
        "Then click Save\n"
        "```\n"
        "\n"
        "When the user logs in\n"
        "Then access is granted\n"
    )
    findings = _spec_gherkin_then_imperative(spec, CATALOG)
    assert findings == []


def test_then_a_system_state_silent() -> None:
    """Then clause starting with 'a' (indefinite article) → silent."""
    spec = _make_spec(
        "# Spec\n\n"
        "Scenario: email sent\n"
        "  Given the registration form is submitted\n"
        "  When the backend processes the request\n"
        "  Then a confirmation email is sent to the user\n"
    )
    findings = _spec_gherkin_then_imperative(spec, CATALOG)
    assert findings == []


def test_and_after_when_with_action_verb_silent() -> None:
    """And step continuing a When (not Then) with action verb → silent."""
    spec = _make_spec(
        "# Spec\n\n"
        "Scenario: multi-action when\n"
        "  Given the user is logged in\n"
        "  When the user opens the settings page\n"
        "  And the user clicks Save\n"
        "  Then the settings are stored\n"
    )
    findings = _spec_gherkin_then_imperative(spec, CATALOG)
    assert findings == []


def test_plan_artifact_silent() -> None:
    """Plan artifact (not spec) → silent."""
    art = Artifact(
        path="plan.md",
        type=ArtifactType.PLAN,
        raw=(
            "# Plan\n\n"
            "Scenario: deploy\n"
            "  Given infra is ready\n"
            "  When pipeline runs\n"
            "  Then click Deploy\n"
        ),
        sections=parse_sections(
            "# Plan\n\n"
            "Scenario: deploy\n"
            "  Given infra is ready\n"
            "  When pipeline runs\n"
            "  Then click Deploy\n"
        ),
    )
    findings = _spec_gherkin_then_imperative(art, CATALOG)
    assert findings == []


def test_then_starts_with_action_verb_in_prose_not_step_silent() -> None:
    """'Then' used in prose (no Gherkin structure) with action verb → silent (no When guard)."""
    spec = _make_spec(
        "# Spec\n\n"
        "## Description\n\n"
        "Then click the button to proceed.\n"
        "Then navigate to the confirmation page.\n"
    )
    findings = _spec_gherkin_then_imperative(spec, CATALOG)
    assert findings == []
