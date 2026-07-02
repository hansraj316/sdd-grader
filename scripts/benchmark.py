#!/usr/bin/env python
"""Benchmark + regression gate for the improvement loop and CI.

Runs the reviewer over the committed fixture specs and asserts the quality gate still
discriminates (good == 100, bad < 70) and that the bad fixture still trips its key
pitfalls. Stores the scored results under reports/benchmarks/ so the loop can track
quality over time. Exits non-zero on any regression — this is the objective gate.

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
from sddgrade.discovery import discover_artifacts, get_adapter
from sddgrade.engine import lint as lint_mod
from sddgrade.engine import scoring

ROOT = Path(__file__).resolve().parent.parent
FIXTURES = ROOT / "tests" / "fixtures"
CORPUS = ROOT / "corpus" / "cases"
OUT_DIR = ROOT / "reports" / "benchmarks"

# Corpus quality floors. Recall = expected pitfalls actually caught.
MIN_RECALL = 0.9

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


def evaluate_corpus_case(case_dir: Path) -> dict:
    """Run the reviewer on one labeled corpus spec and compare to its labels."""
    spec = case_dir / "spec.md"
    labels = json.loads((case_dir / "expected.json").read_text(encoding="utf-8"))
    adapter = SpecKitAdapter()
    cfg = config_mod.Config()
    art = adapter.parse(spec, case_dir)
    findings = lint_mod.lint([art], adapter, case_dir)
    result = scoring.score([art], findings, cfg)

    detected = {f.pitfall_id for f in findings if f.pitfall_id}
    expected = set(labels.get("expect_pitfalls", []))
    tp = sorted(expected & detected)
    fn = sorted(expected - detected)               # missed (false negatives)
    unexpected = sorted(detected - expected)        # not labeled (possible false positives)
    band = labels.get("score_band", [0, 100])
    in_band = band[0] <= result.overall <= band[1]

    return {
        "case": case_dir.name,
        "quality": labels.get("quality"),
        "overall": round(result.overall, 1),
        "score_band": band,
        "in_band": in_band,
        "true_positives": tp,
        "false_negatives": fn,
        "unexpected": unexpected,
        "recall": round(len(tp) / len(expected), 2) if expected else 1.0,
        "note": labels.get("note", ""),
    }


def evaluate_corpus() -> dict:
    if not CORPUS.is_dir():
        return {"cases": [], "summary": {}}
    cases = [evaluate_corpus_case(c) for c in sorted(CORPUS.iterdir()) if (c / "spec.md").is_file()]
    recalls = [c["recall"] for c in cases]
    # "excellent" (no expected pitfalls) is the false-positive guard: it must be clean.
    fp_on_clean = sum(len(c["unexpected"]) for c in cases if not c["true_positives"] and not c["false_negatives"] and c["quality"] == "high")
    summary = {
        "n": len(cases),
        "mean_recall": round(sum(recalls) / len(recalls), 2) if recalls else 1.0,
        "band_failures": [c["case"] for c in cases if not c["in_band"]],
        "false_positives_on_high_quality": fp_on_clean,
    }
    return {"cases": cases, "summary": summary}


def main(argv: list[str]) -> int:
    extra = [Path(p) for p in argv[1:]]

    good = benchmark(FIXTURES / "speckit_good")
    bad = benchmark(FIXTURES / "speckit_bad")
    extras = [benchmark(p) for p in extra if p.is_dir()]
    corpus = evaluate_corpus()

    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "good": good,
        "bad": bad,
        "extras": extras,
        "corpus": corpus,
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

    # Corpus gates: each case must land in its labeled score band, recall floor holds,
    # and high-quality cases must produce no findings (false-positive guard).
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
        if cs["false_positives_on_high_quality"] > 0:
            failures.append(
                f"false positives on high-quality corpus cases: {cs['false_positives_on_high_quality']}"
            )
        if cs["mean_recall"] < MIN_RECALL:
            failures.append(f"corpus mean recall {cs['mean_recall']} < {MIN_RECALL}")

    print(json.dumps({
        "good": good["overall"], "bad": bad["overall"],
        "bad_pitfalls": len(bad["pitfalls"]),
        "corpus": cs,
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
