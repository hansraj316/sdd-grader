"""Tests for SPEC-EARS-WHILE-EVENT-TRIGGER pitfall.

Fires when an EARS While-clause contains a discrete user action verb (click, submit,
select, enter, navigate, etc.) instead of a persistent system state — misusing the
EARS state-driven pattern (Mavin et al. RE 2009; ISO/IEC/IEEE 29148:2018 Annex C).

Guard conditions (all must hold on a non-fenced requirement-bearing line):
  1. Line contains 'shall'.
  2. Line matches: \\bwhile\\b + discrete-action-verb + \\bshall\\b (in order).

Applies to spec artifacts only. One aggregate finding anchored at the first offending line.
"""

from __future__ import annotations

from sddgrade.adapters.base import parse_sections
from sddgrade.catalog import load_catalog
from sddgrade.engine.lint import _spec_ears_while_event_trigger
from sddgrade.model import Artifact, ArtifactType


def _make_spec(raw: str) -> Artifact:
    return Artifact(
        path="spec.md",
        type=ArtifactType.SPEC,
        raw=raw,
        sections=parse_sections(raw),
    )


def _make_plan(raw: str) -> Artifact:
    return Artifact(
        path="plan.md",
        type=ArtifactType.PLAN,
        raw=raw,
        sections=parse_sections(raw),
    )


CATALOG = load_catalog()


# ---------------------------------------------------------------------------
# FIRE cases — check should trigger
# ---------------------------------------------------------------------------


def test_while_user_submits_fires() -> None:
    """'While the user submits the form, the system shall validate' — fires."""
    raw = (
        "## Requirements\n\n"
        "NFR-007: While the user submits the form, the system shall validate the input within 100ms.\n"
    )
    findings = _spec_ears_while_event_trigger(_make_spec(raw), CATALOG)
    assert len(findings) == 1
    assert findings[0].pitfall_id == "SPEC-EARS-WHILE-EVENT-TRIGGER"


def test_while_user_clicks_fires() -> None:
    """'While the user clicks the submit button, the system shall respond' — fires."""
    raw = (
        "## Requirements\n\n"
        "FR-003: While the user clicks the button, the system shall respond within 200ms.\n"
    )
    findings = _spec_ears_while_event_trigger(_make_spec(raw), CATALOG)
    assert len(findings) == 1
    assert findings[0].pitfall_id == "SPEC-EARS-WHILE-EVENT-TRIGGER"


def test_while_user_selects_fires() -> None:
    """'While the user selects a plan, the system shall display pricing' — fires."""
    raw = (
        "## Requirements\n\n"
        "FR-012: While the user selects a subscription plan, the system shall display pricing details.\n"
    )
    findings = _spec_ears_while_event_trigger(_make_spec(raw), CATALOG)
    assert len(findings) == 1


def test_while_user_navigates_fires() -> None:
    """'While the user navigates to checkout, the system shall persist the cart' — fires."""
    raw = (
        "## Requirements\n\n"
        "FR-020: While the user navigates to the checkout page, the system shall persist the cart state.\n"
    )
    findings = _spec_ears_while_event_trigger(_make_spec(raw), CATALOG)
    assert len(findings) == 1


def test_while_user_uploads_fires() -> None:
    """'While the user uploads a file, the system shall validate the format' — fires."""
    raw = (
        "## Requirements\n\n"
        "NFR-015: While the user uploads a file, the system shall validate the file format.\n"
    )
    findings = _spec_ears_while_event_trigger(_make_spec(raw), CATALOG)
    assert len(findings) == 1


def test_multiple_while_event_lines_aggregate() -> None:
    """Two While-with-action-verb lines produce one aggregate finding with count."""
    raw = (
        "## Requirements\n\n"
        "FR-001: While the user clicks the button, the system shall respond.\n"
        "FR-002: While the user submits the form, the system shall validate the input.\n"
    )
    findings = _spec_ears_while_event_trigger(_make_spec(raw), CATALOG)
    assert len(findings) == 1  # one aggregate finding
    assert "2" in findings[0].message  # count reported


# ---------------------------------------------------------------------------
# SILENT cases — check must NOT trigger
# ---------------------------------------------------------------------------


def test_when_user_clicks_silent() -> None:
    """'When the user clicks...' — correct EARS keyword, silent."""
    raw = (
        "## Requirements\n\n"
        "FR-003: When the user clicks the submit button, the system shall validate the form.\n"
    )
    findings = _spec_ears_while_event_trigger(_make_spec(raw), CATALOG)
    assert findings == []


def test_while_user_is_authenticated_silent() -> None:
    """'While the user is authenticated...' — persistent state, correct While usage, silent."""
    raw = (
        "## Requirements\n\n"
        "FR-010: While the user is authenticated, the system shall display the dashboard.\n"
    )
    findings = _spec_ears_while_event_trigger(_make_spec(raw), CATALOG)
    assert findings == []


def test_while_session_active_silent() -> None:
    """'While the checkout session is active...' — persistent state, correct While usage, silent."""
    raw = (
        "## Requirements\n\n"
        "FR-011: While the checkout session is active, the system shall maintain the cart contents.\n"
    )
    findings = _spec_ears_while_event_trigger(_make_spec(raw), CATALOG)
    assert findings == []


def test_no_shall_silent() -> None:
    """While + action verb but no 'shall' — not normative, silent."""
    raw = (
        "## Requirements\n\n"
        "While the user submits the form, the system may validate the input.\n"
    )
    findings = _spec_ears_while_event_trigger(_make_spec(raw), CATALOG)
    assert findings == []


def test_fenced_block_excluded() -> None:
    """While-event trigger inside a fenced code block — silent."""
    raw = (
        "## Requirements\n\n"
        "```\n"
        "FR-005: While the user clicks the button, the system shall respond.\n"
        "```\n"
    )
    findings = _spec_ears_while_event_trigger(_make_spec(raw), CATALOG)
    assert findings == []


def test_plain_requirement_no_while_silent() -> None:
    """Plain normative requirement with no While-clause — silent."""
    raw = (
        "## Requirements\n\n"
        "FR-001: The system shall respond within 200ms (p95) under 500 concurrent users.\n"
    )
    findings = _spec_ears_while_event_trigger(_make_spec(raw), CATALOG)
    assert findings == []


def test_plan_artifact_silent() -> None:
    """Plan artifact — pitfall applies to spec only, silent."""
    raw = (
        "## Deployment\n\n"
        "FR-001: While the user submits the form, the system shall validate the input.\n"
    )
    findings = _spec_ears_while_event_trigger(_make_plan(raw), CATALOG)
    assert findings == []


def test_while_mode_enabled_silent() -> None:
    """'While maintenance mode is enabled...' — system mode state, correct While, silent."""
    raw = (
        "## Requirements\n\n"
        "NFR-008: While maintenance mode is enabled, the system shall return HTTP 503 for all API requests.\n"
    )
    findings = _spec_ears_while_event_trigger(_make_spec(raw), CATALOG)
    assert findings == []


def test_while_no_action_verb_silent() -> None:
    """While-clause with 'shall' but no action verb — not a keyword-choice error, silent."""
    raw = (
        "## Requirements\n\n"
        "NFR-002: While the backup is in progress, the system shall prevent write operations.\n"
    )
    findings = _spec_ears_while_event_trigger(_make_spec(raw), CATALOG)
    assert findings == []
