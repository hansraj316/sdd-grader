"""OpenSpec adapter + auto-detection (issue #20)."""

from __future__ import annotations

from pathlib import Path

from sddgrade import config as config_mod
from sddgrade.adapters.openspec import OpenSpecAdapter
from sddgrade.adapters.speckit import SpecKitAdapter
from sddgrade.discovery import discover_artifacts, resolve_adapter
from sddgrade.engine import lint as lint_mod
from sddgrade.engine import scoring
from sddgrade.model import ArtifactType

FIXTURES = Path(__file__).parent / "fixtures"
OS_GOOD = FIXTURES / "openspec_good"
OS_BAD = FIXTURES / "openspec_bad"
SK_GOOD = FIXTURES / "speckit_good"


def test_detection():
    assert OpenSpecAdapter().detect(OS_GOOD)
    assert not SpecKitAdapter().detect(OS_GOOD)
    # Spec-Kit repos are unaffected.
    assert SpecKitAdapter().detect(SK_GOOD)
    assert not OpenSpecAdapter().detect(SK_GOOD)


def test_auto_resolves_correctly():
    assert resolve_adapter(OS_GOOD, "auto").name == "openspec"
    assert resolve_adapter(SK_GOOD, "auto").name == "speckit"


def test_discovery_and_classification():
    arts = discover_artifacts(OS_GOOD, "auto")
    types = {a.type for a in arts}
    assert ArtifactType.SPEC in types          # capability + delta specs
    assert ArtifactType.PLAN in types          # proposal.md
    assert ArtifactType.TASKS in types         # tasks.md
    assert ArtifactType.CONSTITUTION in types  # project.md
    # Change-id / capability becomes the feature id.
    assert any(a.feature_id == "add-oauth" for a in arts)
    assert any(a.feature_id == "auth" for a in arts)


def _score(root: Path):
    adapter = resolve_adapter(root, "auto")
    arts = discover_artifacts(root, "auto")
    findings = lint_mod.lint(arts, adapter, root)
    return scoring.score(arts, findings, config_mod.Config()), findings


def test_good_openspec_is_clean():
    result, findings = _score(OS_GOOD)
    assert result.overall == 100.0
    assert findings == [], [f.message for f in findings]


def test_bad_openspec_flags_missing_scenario():
    result, findings = _score(OS_BAD)
    ids = {f.pitfall_id for f in findings}
    assert "OPENSPEC-REQ-NO-SCENARIO" in ids
    assert result.overall < 100.0


def test_explicit_tool_selection():
    arts = discover_artifacts(OS_GOOD, "openspec")
    assert arts and all(a.path.endswith(".md") for a in arts)


def test_speckit_structural_checks_do_not_run_on_openspec():
    # Spec-Kit-only pitfalls (e.g. Constitution Check) must not fire on OpenSpec.
    _result, findings = _score(OS_BAD)
    ids = {f.pitfall_id for f in findings}
    assert "PLAN-CONSTITUTION-UNCHECKED" not in ids
