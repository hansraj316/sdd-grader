#!/usr/bin/env python
"""Benchmark + regression gate for the improvement loop and CI.

Runs the reviewer over the committed fixture specs and the labeled corpus, asserting:

* the fixture gate still discriminates (good == 100, bad < 70, key pitfalls trip);
* every corpus case lands in its labeled score band (bands carry a documented
  rationale in expected.json — see #55);
* recall: every labeled expected pitfall is caught (floor MIN_RECALL). Pitfalls a
  case documents as ``known_misses`` (defects lint SHOULD catch but currently
  doesn't — #53) are excluded from the gated recall but reported in
  ``recall_incl_known_misses`` so the gap stays visible;
* precision (#56): labeled-correct detections / all detections, with a floor
  (MIN_PRECISION). ``accepted_extras`` count as correct; detections labeled
  ``known_false_positives`` count against precision; any detection with NO label
  at all fails the gate outright;
* the judge path (#54): golden judge responses (corpus/cases/*/judge.golden.json)
  are pushed through the real agent-judge pipeline (freshness manifest ->
  read_judgment -> to_findings -> merge -> score) offline, with expected merged
  scores, pitfall sets, artifact attribution, and enum normalization.

Corpus cases may be a single top-level spec.md or a full feature tree
(specs/<id>/… or an openspec/ change — #57); multi-file cases go through the same
discovery the CLI uses. Results are stored under reports/benchmarks/ so the loop can
track quality over time. Exits non-zero on any regression — this is the objective gate.

Usage:
    python scripts/benchmark.py            # run the regression gate, store results
    python scripts/benchmark.py <path>...  # also benchmark arbitrary spec dirs (no gate)
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from sddgrade import config as config_mod
from sddgrade.adapters.speckit import SpecKitAdapter
from sddgrade.discovery import discover_artifacts, get_adapter, resolve_adapter
from sddgrade.engine import judge as judge_mod
from sddgrade.engine import lint as lint_mod
from sddgrade.engine import scoring
from sddgrade.integrations.agent import JUDGMENT_FILE, artifact_manifest

ROOT = Path(__file__).resolve().parent.parent
FIXTURES = ROOT / "tests" / "fixtures"
CORPUS = ROOT / "corpus" / "cases"
OUT_DIR = ROOT / "reports" / "benchmarks"

# Corpus quality floors. Recall = labeled expected pitfalls actually caught
# (known_misses are documented gaps, excluded from the gated number but reported).
MIN_RECALL = 0.9

# Precision floor (#56): labeled-correct detections / all detections, micro-averaged
# across the corpus. Measured 0.958 at gate introduction (23 of 24 detections labeled
# correct; the single uncredited one is the labeled known-false-positive 'scalable'
# hit on benign-lookalike). Floor 0.95 sits just under that so the gate passes today
# while locking the level in: one additional false positive anywhere in the corpus
# (e.g. 23/25 = 0.92) trips it — noisy rules can no longer proliferate unseen.
MIN_PRECISION = 0.95

# Regression expectations. Tighten over time as the engine improves.
EXPECT_GOOD_MIN = 100.0
EXPECT_BAD_MAX = 70.0
EXPECT_BAD_PITFALLS = {
    "SPEC-UNRESOLVED-CLARIFICATION",
    "SPEC-LEFTOVER-PLACEHOLDER",
    "PLAN-CONSTITUTION-UNCHECKED",
    "CONST-PLACEHOLDER",
}


def benchmark(path: Path) -> dict:
    cfg = config_mod.Config()
    adapter = get_adapter(cfg.tool)
    arts = discover_artifacts(path, cfg.tool)
    findings = lint_mod.lint(arts, adapter, path)
    result = scoring.score(arts, findings, cfg)
    pitfalls = sorted({f.pitfall_id for f in findings if f.pitfall_id})
    return {
        "path": str(path),
        "overall": round(result.overall, 1),
        "artifacts": [
            {"type": a.type.value, "overall": round(a.overall, 1), "findings": len(a.findings)}
            for a in result.artifacts
        ],
        "pitfalls": pitfalls,
        "finding_count": len(findings),
    }


def _case_artifacts(case_dir: Path):
    """Parse a corpus case's artifacts: a single top-level spec.md, or a full
    feature tree routed through the same adapter discovery the CLI uses (#57)."""
    spec = case_dir / "spec.md"
    if spec.is_file():
        adapter = SpecKitAdapter()
        return adapter, [adapter.parse(spec, case_dir)]
    adapter = resolve_adapter(case_dir, "auto")
    return adapter, [adapter.parse(p, case_dir) for p in adapter.discover(case_dir)]


def evaluate_corpus_case(case_dir: Path) -> dict:
    """Run the reviewer on one labeled corpus case and compare to its labels.

    Label vocabulary (expected.json):
      expect_pitfalls        must be detected (miss = false negative, gated)
      accepted_extras        genuine defects beyond the case's point; count as
                             correct detections for precision, not gated as FNs
      known_misses           defects lint SHOULD catch but currently doesn't (#53);
                             excluded from gated recall, reported separately
      known_false_positives  wrong-but-current detections (#56); count against
                             precision, exempt from the unlabeled-unexpected gate
    Anything detected outside all four lists is *unlabeled* — gated to zero.
    """
    labels = json.loads((case_dir / "expected.json").read_text(encoding="utf-8"))
    adapter, arts = _case_artifacts(case_dir)
    cfg = config_mod.Config()
    findings = lint_mod.lint(arts, adapter, case_dir)
    result = scoring.score(arts, findings, cfg)

    detected = {f.pitfall_id for f in findings if f.pitfall_id}
    expected = set(labels.get("expect_pitfalls", []))
    extras = set(labels.get("accepted_extras", []))
    known_misses = set(labels.get("known_misses", []))
    known_fps = set(labels.get("known_false_positives", []))

    tp = sorted(expected & detected)
    fn = sorted(expected - detected)                # missed (false negatives, gated)
    extras_detected = sorted(extras & detected)
    km_caught = sorted(known_misses & detected)     # a documented gap got fixed
    km_missed = sorted(known_misses - detected)     # still missed (visible, not gated)
    kfp_detected = sorted(known_fps & detected)
    unlabeled = sorted(detected - expected - extras - known_misses - known_fps)

    correct = len(tp) + len(extras_detected) + len(km_caught)
    honest_pool = expected | known_misses
    band = labels.get("score_band", [0, 100])
    in_band = band[0] <= result.overall <= band[1]

    return {
        "case": case_dir.name,
        "quality": labels.get("quality"),
        "adapter": adapter.name,
        "artifact_count": len(arts),
        "overall": round(result.overall, 1),
        "score_band": band,
        "band_rationale": labels.get("band_rationale", ""),
        "in_band": in_band,
        "true_positives": tp,
        "false_negatives": fn,
        "accepted_extras_detected": extras_detected,
        "known_misses_caught": km_caught,
        "known_misses_missed": km_missed,
        "known_false_positives_detected": kfp_detected,
        "unexpected": unlabeled,                    # unlabeled detections (gated to zero)
        "recall": round(len(tp) / len(expected), 2) if expected else 1.0,
        "recall_incl_known_misses": (
            round(len(honest_pool & detected) / len(honest_pool), 2) if honest_pool else 1.0
        ),
        "precision": round(correct / len(detected), 2) if detected else 1.0,
        "correct_detections": correct,
        "total_detections": len(detected),
        "note": labels.get("note", ""),
    }


def evaluate_corpus() -> dict:
    if not CORPUS.is_dir():
        return {"cases": [], "summary": {}}
    cases = [
        evaluate_corpus_case(c)
        for c in sorted(CORPUS.iterdir())
        if (c / "expected.json").is_file()
    ]
    recalls = [c["recall"] for c in cases]
    honest_recalls = [c["recall_incl_known_misses"] for c in cases]
    correct = sum(c["correct_detections"] for c in cases)
    detections = sum(c["total_detections"] for c in cases)
    # High-quality cases (the negative controls) must produce no *unlabeled* findings.
    fp_on_clean = sum(len(c["unexpected"]) for c in cases if c["quality"] == "high")
    summary = {
        "n": len(cases),
        "mean_recall": round(sum(recalls) / len(recalls), 2) if recalls else 1.0,
        # The honest number (#53): includes documented known_misses. Reported, not gated.
        "mean_recall_incl_known_misses": (
            round(sum(honest_recalls) / len(honest_recalls), 2) if honest_recalls else 1.0
        ),
        # Micro-averaged precision (#56): labeled-correct / all detections.
        "precision": round(correct / detections, 3) if detections else 1.0,
        "correct_detections": correct,
        "total_detections": detections,
        "band_failures": [c["case"] for c in cases if not c["in_band"]],
        "unlabeled_unexpected": {c["case"]: c["unexpected"] for c in cases if c["unexpected"]},
        "known_false_positives": sum(len(c["known_false_positives_detected"]) for c in cases),
        "false_positives_on_high_quality": fp_on_clean,
    }
    return {"cases": cases, "summary": summary}


# --------------------------------------------------------------------- judge path (#54)

def evaluate_judge_case(case_dir: Path) -> dict:
    """Push a golden judge response through the REAL agent-judge pipeline, offline.

    The fixture (judge.golden.json) holds a hand-authored raw judge output plus
    expectations. Because read_judgment rejects any judgment whose hash manifest
    doesn't match the artifacts on disk, the manifest is generated at runtime and a
    transient .sddgrade/judge.json is written into the case dir (removed after).
    This deterministically exercises: the manifest freshness check, to_findings
    normalization (enum synonyms, defaults), artifact attribution (relative path /
    unique basename / unattributed bucket), and the merged lint+judge scoring.
    """
    fixture = json.loads((case_dir / "judge.golden.json").read_text(encoding="utf-8"))
    expect = fixture["expect"]
    adapter, arts = _case_artifacts(case_dir)
    cfg = config_mod.Config()
    lint_findings = lint_mod.lint(arts, adapter, case_dir)

    judge_file = case_dir / JUDGMENT_FILE
    created_dir = not judge_file.parent.exists()
    judge_file.parent.mkdir(parents=True, exist_ok=True)
    try:
        judge_file.write_text(
            json.dumps(
                {
                    # Content hashes must match what's on disk, so the manifest is
                    # generated here, at runtime — never stored in the fixture.
                    "artifacts": artifact_manifest(arts, case_dir),
                    "findings": fixture["findings"],
                }
            ),
            encoding="utf-8",
        )
        judge_findings, _notes, _model = judge_mod.judge(arts, "agent", case_dir, cfg)
    finally:
        judge_file.unlink(missing_ok=True)
        if created_dir:
            judge_file.parent.rmdir()

    result = scoring.score(arts, lint_findings + judge_findings, cfg, engine="agent")
    overall = round(result.overall, 1)

    judge_pitfalls = sorted({f.pitfall_id for f in judge_findings if f.pitfall_id})
    # Attribution: an expectation of "(unattributed)" means the finding must name no
    # discovered artifact AND land in scoring's synthetic "(unattributed)" review —
    # kept visible, never silently dropped. Otherwise the resolved path must match.
    art_paths = {a.path for a in arts}
    unattributed = next(
        (r for r in result.artifacts if r.path == scoring.UNATTRIBUTED_PATH), None
    )
    attribution_ok: list[bool] = []
    for f, want in zip(judge_findings, expect["attribution"]):
        got = f.artifact_path or ""
        if want == "(unattributed)":
            ok = got not in art_paths and unattributed is not None and f in unattributed.findings
        else:
            ok = got.endswith(want)
        attribution_ok.append(ok)
    normalization_ok = [
        f.severity.value == want["severity"] and f.dimension.value == want["dimension"]
        for f, want in zip(judge_findings, expect["normalized"])
    ]

    checks = {
        "findings_preserved": len(judge_findings) == len(fixture["findings"]),
        "score_matches": overall == expect["merged_overall"],
        "pitfalls_match": judge_pitfalls == sorted(expect["judge_pitfalls"]),
        "attribution": all(attribution_ok) and len(attribution_ok) == len(judge_findings),
        "normalization": all(normalization_ok) and len(normalization_ok) == len(judge_findings),
        "source_is_judge": all(f.source.value == "judge" for f in judge_findings),
    }
    return {
        "case": case_dir.name,
        "merged_overall": overall,
        "expected_overall": expect["merged_overall"],
        "judge_pitfalls": judge_pitfalls,
        "checks": checks,
        "pass": all(checks.values()),
    }


def evaluate_judge_path() -> dict:
    if not CORPUS.is_dir():
        return {"cases": [], "summary": {}}
    cases = [
        evaluate_judge_case(c)
        for c in sorted(CORPUS.iterdir())
        if (c / "judge.golden.json").is_file()
    ]
    failures = [
        f"{c['case']}: {', '.join(k for k, ok in c['checks'].items() if not ok)}"
        for c in cases
        if not c["pass"]
    ]
    return {"cases": cases, "summary": {"n": len(cases), "failures": failures}}


def main(argv: list[str]) -> int:
    extra = [Path(p) for p in argv[1:]]

    good = benchmark(FIXTURES / "speckit_good")
    bad = benchmark(FIXTURES / "speckit_bad")
    extras = [benchmark(p) for p in extra if p.is_dir()]
    corpus = evaluate_corpus()
    judge_path = evaluate_judge_path()

    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "good": good,
        "bad": bad,
        "extras": extras,
        "corpus": corpus,
        "judge_path": judge_path,
    }

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "latest.json").write_text(json.dumps(report, indent=2), encoding="utf-8")

    failures: list[str] = []
    if good["overall"] < EXPECT_GOOD_MIN:
        failures.append(f"good fixture regressed: {good['overall']} < {EXPECT_GOOD_MIN}")
    if bad["overall"] >= EXPECT_BAD_MAX:
        failures.append(f"bad fixture not failing: {bad['overall']} >= {EXPECT_BAD_MAX}")
    missing = EXPECT_BAD_PITFALLS - set(bad["pitfalls"])
    if missing:
        failures.append(f"bad fixture stopped tripping pitfalls: {sorted(missing)}")

    # Corpus gates: each case lands in its labeled band, misses no expected pitfall,
    # and produces no UNLABELED detection; recall and precision floors hold.
    cs = corpus["summary"]
    if cs:
        for case in corpus["cases"]:
            if not case["in_band"]:
                failures.append(
                    f"corpus '{case['case']}' score {case['overall']} outside band {case['score_band']}"
                )
            if case["false_negatives"]:
                failures.append(
                    f"corpus '{case['case']}' missed expected pitfalls: {case['false_negatives']}"
                )
            if case["unexpected"]:
                failures.append(
                    f"corpus '{case['case']}' has unlabeled detections: {case['unexpected']} "
                    "(label them in expected.json as accepted_extras or known_false_positives)"
                )
        if cs["false_positives_on_high_quality"] > 0:
            failures.append(
                f"unlabeled false positives on high-quality corpus cases: {cs['false_positives_on_high_quality']}"
            )
        if cs["mean_recall"] < MIN_RECALL:
            failures.append(f"corpus mean recall {cs['mean_recall']} < {MIN_RECALL}")
        if cs["precision"] < MIN_PRECISION:
            failures.append(f"corpus precision {cs['precision']} < {MIN_PRECISION}")

    # Judge-path gate (#54): the offline golden-judge pipeline must reproduce the
    # expected merged scores, attribution, and normalization exactly.
    js = judge_path["summary"]
    if js:
        for msg in js["failures"]:
            failures.append(f"judge path: {msg}")
        if js["n"] < 2:
            failures.append(f"judge path: expected >= 2 golden cases, found {js['n']}")

    print(json.dumps({
        "good": good["overall"], "bad": bad["overall"],
        "bad_pitfalls": len(bad["pitfalls"]),
        "corpus": cs,
        "judge_path": js,
        "pass": not failures,
    }, indent=2))
    if failures:
        for f in failures:
            print(f"REGRESSION: {f}", file=sys.stderr)
        return 1
    print("benchmark gate: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
