"""SARIF output (issues #14, #66)."""

from __future__ import annotations

import json
from pathlib import Path

from sddgrade import config as config_mod
from sddgrade.discovery import discover_artifacts, get_adapter
from sddgrade.engine import lint as lint_mod
from sddgrade.engine import scoring
from sddgrade.model import (
    ArtifactReview,
    ArtifactType,
    Dimension,
    DimensionScore,
    Finding,
    ReviewResult,
    Severity,
    Source,
)
from sddgrade.report import sarif


def _result(repo: Path):
    cfg = config_mod.Config()
    adapter = get_adapter(cfg.tool)
    arts = discover_artifacts(repo)
    findings = lint_mod.lint(arts, adapter, repo)
    return scoring.score(arts, findings, cfg)


def _synthetic_result(findings: list[Finding]) -> ReviewResult:
    ds = DimensionScore(
        dimension=Dimension.CLARITY, score=50, penalty=50, findings=findings
    )
    ar = ArtifactReview(
        path="spec.md", type=ArtifactType.SPEC, feature_id="x", dimension_scores=[ds]
    )
    return ReviewResult(artifacts=[ar], engine="rules")


def _finding(path: str | None, sev: Severity = Severity.MEDIUM,
             pitfall_id: str | None = None, line: int | None = None) -> Finding:
    return Finding(
        dimension=Dimension.CLARITY,
        severity=sev,
        message="a finding",
        suggestion="fix it",
        source=Source.LINT,
        pitfall_id=pitfall_id,
        artifact_path=path,
        line=line,
    )


def test_sarif_is_valid_structure(bad_repo: Path):
    doc = json.loads(sarif.render(_result(bad_repo), root=bad_repo))
    assert doc["version"] == "2.1.0"
    run = doc["runs"][0]
    assert run["tool"]["driver"]["name"] == "sddgrade"
    assert run["tool"]["driver"]["rules"]
    assert run["results"]
    r = run["results"][0]
    assert {"ruleId", "level", "message", "locations"} <= set(r)
    assert r["level"] in {"error", "warning", "note"}
    # Pitfall ids become rule ids.
    rule_ids = {rule["id"] for rule in run["tool"]["driver"]["rules"]}
    assert any(rid.startswith("SPEC-") for rid in rule_ids)


def test_sarif_paths_are_relative(bad_repo: Path):
    doc = json.loads(sarif.render(_result(bad_repo), root=bad_repo))
    for res in doc["runs"][0]["results"]:
        uri = res["locations"][0]["physicalLocation"]["artifactLocation"]["uri"]
        assert not uri.startswith("/")  # relative to the repo root


def test_sarif_clean_repo_has_no_results(good_repo: Path):
    doc = json.loads(sarif.render(_result(good_repo), root=good_repo))
    assert doc["runs"][0]["results"] == []


# --------------------------------------------------------------------------- #66: schema validity


def test_sarif_required_properties(bad_repo: Path):
    """Structural check against SARIF 2.1.0 required properties.

    (jsonschema is not a dev dependency; these mirror the schema's `required`
    lists for sarifLog, run, toolComponent, reportingDescriptor and result.)
    """
    doc = json.loads(sarif.render(_result(bad_repo), root=bad_repo))
    # sarifLog: required [version, runs]
    assert doc["version"] == "2.1.0"
    assert isinstance(doc["runs"], list) and doc["runs"]
    run = doc["runs"][0]
    # run: required [tool]; toolComponent: required [name]
    assert run["tool"]["driver"]["name"]
    for rule in run["tool"]["driver"]["rules"]:
        # reportingDescriptor: required [id]
        assert rule["id"]
        assert rule["defaultConfiguration"]["level"] in {"none", "note", "warning", "error"}
    for res in run["results"]:
        # result: required [message]
        assert res["message"]["text"]
        assert res["level"] in {"none", "note", "warning", "error"}
        for loc in res.get("locations", []):
            uri = loc["physicalLocation"]["artifactLocation"]["uri"]
            assert uri  # never an empty URI (breaks GitHub upload)


def test_sarif_omits_location_when_no_artifact_path():
    result = _synthetic_result([_finding(path=None)])
    doc = json.loads(sarif.render(result, root=Path("/repo")))
    res = doc["runs"][0]["results"][0]
    assert "locations" not in res
    assert '"uri": ""' not in sarif.render(result, root=Path("/repo"))


def test_sarif_omits_location_for_out_of_root_paths(tmp_path: Path):
    outside = tmp_path / "elsewhere" / "spec.md"
    result = _synthetic_result([_finding(path=str(outside), line=3)])
    doc = json.loads(sarif.render(result, root=tmp_path / "repo"))
    assert "locations" not in doc["runs"][0]["results"][0]


def test_sarif_uris_are_posix_relative(bad_repo: Path):
    doc = json.loads(sarif.render(_result(bad_repo), root=bad_repo))
    uris = [
        res["locations"][0]["physicalLocation"]["artifactLocation"]["uri"]
        for res in doc["runs"][0]["results"]
        if "locations" in res
    ]
    assert uris
    for uri in uris:
        assert "\\" not in uri
        assert not uri.startswith("/")
        assert not Path(uri).is_absolute()


def test_sarif_rule_default_level_matches_result_levels(bad_repo: Path):
    doc = json.loads(sarif.render(_result(bad_repo), root=bad_repo))
    run = doc["runs"][0]
    rank = {"none": 0, "note": 1, "warning": 2, "error": 3}
    default_by_rule = {
        r["id"]: r["defaultConfiguration"]["level"] for r in run["tool"]["driver"]["rules"]
    }
    worst: dict[str, str] = {}
    for res in run["results"]:
        rid = res["ruleId"]
        if rid not in worst or rank[res["level"]] > rank[worst[rid]]:
            worst[rid] = res["level"]
    for rid, level in worst.items():
        assert default_by_rule[rid] == level


def test_sarif_partial_fingerprints_are_stable():
    f = _finding(path="/repo/spec.md", pitfall_id="SPEC-X", line=4)
    result = _synthetic_result([f])
    doc1 = json.loads(sarif.render(result, root=Path("/repo")))
    fp1 = doc1["runs"][0]["results"][0]["partialFingerprints"]["sddgradeFingerprint/v1"]
    assert fp1
    # Rewording the message must not change alert identity.
    f.message = "completely different wording"
    doc2 = json.loads(sarif.render(result, root=Path("/repo")))
    fp2 = doc2["runs"][0]["results"][0]["partialFingerprints"]["sddgradeFingerprint/v1"]
    assert fp1 == fp2
