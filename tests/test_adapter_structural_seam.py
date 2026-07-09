"""Tests for issue #48: lint engine uses adapter hooks instead of name-branching.

Verifies:
- Both adapters expose `hint`, `structural_checks`, `cross_artifact_checks`.
- lint() delegates structural/cross-artifact work through the adapter hook,
  not via `if adapter.name == "speckit"` branching.
- Missing-section suggestions carry the adapter's name, not a hard-coded "Spec-Kit".
- runner.py no-artifacts message uses adapter.hint (tool-agnostic).
- A mock adapter with no structural checks produces no findings from those layers.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from sddgrade import config as config_mod
from sddgrade.adapters.openspec import OpenSpecAdapter
from sddgrade.adapters.speckit import SpecKitAdapter
from sddgrade.catalog import load_catalog
from sddgrade.discovery import resolve_adapter
from sddgrade.engine import lint as lint_mod
from sddgrade.model import Artifact, ArtifactType, Dimension, Finding, Section, Severity, Source
from sddgrade.runner import EXIT_NO_ARTIFACTS, run_review

FIXTURES = Path(__file__).parent / "fixtures"
OS_GOOD = FIXTURES / "openspec_good"
SK_GOOD = FIXTURES / "speckit_good"


# ---------------------------------------------------------------------------
# Protocol surface: hint + hooks must exist on both built-in adapters.


def test_speckit_has_hint():
    assert isinstance(SpecKitAdapter.hint, str) and SpecKitAdapter.hint


def test_openspec_has_hint():
    assert isinstance(OpenSpecAdapter.hint, str) and OpenSpecAdapter.hint


def test_speckit_hint_mentions_specify():
    assert "specify" in SpecKitAdapter.hint.lower() or "spec" in SpecKitAdapter.hint.lower()


def test_speckit_structural_checks_callable():
    adapter = SpecKitAdapter()
    art = _dummy_spec()
    catalog = load_catalog()
    result = adapter.structural_checks(art, catalog)
    assert isinstance(result, list)


def test_openspec_structural_checks_callable():
    adapter = OpenSpecAdapter()
    art = _dummy_spec()
    catalog = load_catalog()
    result = adapter.structural_checks(art, catalog)
    assert isinstance(result, list)


def test_openspec_cross_artifact_checks_returns_empty():
    adapter = OpenSpecAdapter()
    art = _dummy_spec()
    catalog = load_catalog()
    result = adapter.cross_artifact_checks([art], catalog)
    assert result == []


def test_speckit_cross_artifact_checks_callable():
    adapter = SpecKitAdapter()
    art = _dummy_spec()
    catalog = load_catalog()
    result = adapter.cross_artifact_checks([art], catalog)
    assert isinstance(result, list)


# ---------------------------------------------------------------------------
# lint() itself is toolchain-agnostic: no adapter.name branching.


def test_lint_calls_adapter_structural_hook(tmp_path):
    """lint() must call adapter.structural_checks, not branch on adapter.name."""
    adapter = MagicMock(spec=SpecKitAdapter)
    adapter.name = "speckit"
    adapter.hint = "test hint"
    adapter.structural_checks.return_value = []
    adapter.cross_artifact_checks.return_value = []
    adapter.required_sections.return_value = []

    art = _dummy_spec()
    lint_mod.lint([art], adapter, tmp_path)

    adapter.structural_checks.assert_called_once_with(art, load_catalog())


def test_lint_calls_adapter_cross_artifact_hook(tmp_path):
    adapter = MagicMock(spec=SpecKitAdapter)
    adapter.name = "speckit"
    adapter.hint = "test hint"
    adapter.structural_checks.return_value = []
    adapter.cross_artifact_checks.return_value = []
    adapter.required_sections.return_value = []

    arts = [_dummy_spec()]
    lint_mod.lint(arts, adapter, tmp_path)

    adapter.cross_artifact_checks.assert_called_once_with(arts, load_catalog())


def test_lint_includes_findings_from_structural_hook(tmp_path):
    """Findings returned by adapter.structural_checks appear in lint output."""
    sentinel = Finding(
        dimension=Dimension.COMPLETENESS,
        severity=Severity.MEDIUM,
        message="sentinel from hook",
        suggestion="fix it",
        source=Source.LINT,
        pitfall_id="TEST-SENTINEL",
        artifact_path="spec.md",
    )
    adapter = MagicMock(spec=SpecKitAdapter)
    adapter.name = "speckit"
    adapter.hint = "test"
    adapter.structural_checks.return_value = [sentinel]
    adapter.cross_artifact_checks.return_value = []
    adapter.required_sections.return_value = []

    findings = lint_mod.lint([_dummy_spec()], adapter, tmp_path)
    assert sentinel in findings


# ---------------------------------------------------------------------------
# Missing-section suggestion carries adapter name, not hard-coded "Spec-Kit".


def test_missing_section_suggestion_uses_adapter_name(tmp_path):
    """'see the <adapter.name> template' not 'see the Spec-Kit template'."""
    adapter = MagicMock(spec=OpenSpecAdapter)
    adapter.name = "openspec"
    adapter.hint = "openspec hint"
    adapter.required_sections.return_value = ["Requirements"]
    adapter.structural_checks.return_value = []
    adapter.cross_artifact_checks.return_value = []

    # spec with NO "Requirements" heading → missing-section finding.
    art = Artifact(
        path="openspec/changes/x/specs/auth/spec.md",
        type=ArtifactType.SPEC,
        feature_id="x",
        raw="# My Spec\n\nsome body\n",
        sections=[Section(title="My Spec", level=1, body="some body", line=1)],
    )
    findings = lint_mod.lint([art], adapter, tmp_path)
    missing = [f for f in findings if "Requirements" in f.message]
    assert missing, "Expected a missing-section finding for 'Requirements'"
    assert "openspec" in missing[0].suggestion.lower(), (
        f"Suggestion should mention 'openspec', got: {missing[0].suggestion!r}"
    )
    assert "spec-kit" not in missing[0].suggestion.lower(), (
        f"Suggestion must not mention Spec-Kit for openspec adapter: {missing[0].suggestion!r}"
    )


def test_speckit_missing_section_still_mentions_speckit(tmp_path):
    adapter = SpecKitAdapter()
    art = Artifact(
        path="specs/f/spec.md",
        type=ArtifactType.SPEC,
        feature_id="f",
        raw="# My Spec\n\nsome body\n",
        sections=[Section(title="My Spec", level=1, body="some body", line=1)],
    )
    findings = lint_mod.lint([art], adapter, tmp_path)
    missing = [f for f in findings if f.pitfall_id is None and "Missing required section" in f.message]
    assert missing
    assert "speckit" in missing[0].suggestion.lower()


# ---------------------------------------------------------------------------
# runner.py no-artifacts message uses adapter.hint.


def test_runner_no_artifacts_uses_adapter_hint(tmp_path, capsys):
    """When no artifacts are found the message must contain the adapter hint."""
    # tmp_path has no artifacts — no specs/ dir, no openspec/ dir.
    result = run_review(tmp_path)
    assert result == EXIT_NO_ARTIFACTS
    out = capsys.readouterr().out
    # The console.print rich markup goes to stdout via the default Console().
    # We check that the hint text appears somewhere in the output.
    adapter = resolve_adapter(tmp_path, "auto")
    assert adapter.hint[:20] in out or adapter.name in out


# ---------------------------------------------------------------------------
# OpenSpec structural check (req-no-scenario) no longer lives in lint.py.


def test_openspec_req_no_scenario_fires_via_adapter():
    """OPENSPEC-REQ-NO-SCENARIO still fires after moving to openspec.py."""
    adapter = OpenSpecAdapter()
    catalog = load_catalog()
    art = Artifact(
        path="openspec/changes/x/specs/auth/spec.md",
        type=ArtifactType.SPEC,
        feature_id="x",
        raw=(
            "# Auth Spec\n\n"
            "## Requirements\n\n"
            "### Requirement: Login\n\n"
            "The system shall authenticate users.\n"
        ),
        sections=[
            Section(title="Auth Spec", level=1, body="", line=1),
            Section(title="Requirements", level=2, body="", line=3),
            Section(title="Requirement: Login", level=3,
                    body="The system shall authenticate users.", line=5),
        ],
    )
    findings = adapter.structural_checks(art, catalog)
    ids = {f.pitfall_id for f in findings}
    assert "OPENSPEC-REQ-NO-SCENARIO" in ids


def test_openspec_req_with_scenario_is_clean():
    adapter = OpenSpecAdapter()
    catalog = load_catalog()
    art = Artifact(
        path="openspec/changes/x/specs/auth/spec.md",
        type=ArtifactType.SPEC,
        feature_id="x",
        raw=(
            "# Auth Spec\n\n"
            "## Requirements\n\n"
            "### Requirement: Login\n\n"
            "The system shall authenticate users.\n\n"
            "#### Scenario: Happy path\n\n"
            "WHEN the user submits credentials THEN access is granted.\n"
        ),
        sections=[
            Section(title="Auth Spec", level=1, body="", line=1),
            Section(title="Requirements", level=2, body="", line=3),
            Section(title="Requirement: Login", level=3,
                    body="The system shall authenticate users.", line=5),
            Section(title="Scenario: Happy path", level=4,
                    body="WHEN...", line=8),
        ],
    )
    findings = adapter.structural_checks(art, catalog)
    ids = {f.pitfall_id for f in findings}
    assert "OPENSPEC-REQ-NO-SCENARIO" not in ids


# ---------------------------------------------------------------------------
# Helpers.


def _dummy_spec() -> Artifact:
    return Artifact(
        path="specs/f/spec.md",
        type=ArtifactType.SPEC,
        feature_id="f",
        raw="# Feature\n\n## User Scenarios\n\n## Requirements\n\n## Success Criteria\n",
        sections=[
            Section(title="Feature", level=1, body="", line=1),
            Section(title="User Scenarios", level=2, body="", line=3),
            Section(title="Requirements", level=2, body="", line=5),
            Section(title="Success Criteria", level=2, body="", line=7),
        ],
    )
