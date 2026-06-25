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

from sddreview import config as config_mod
from sddreview.discovery import discover_artifacts, get_adapter
from sddreview.engine import lint as lint_mod
from sddreview.engine import scoring

ROOT = Path(__file__).resolve().parent.parent
FIXTURES = ROOT / "tests" / "fixtures"
OUT_DIR = ROOT / "reports" / "benchmarks"

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


def main(argv: list[str]) -> int:
    extra = [Path(p) for p in argv[1:]]

    good = benchmark(FIXTURES / "speckit_good")
    bad = benchmark(FIXTURES / "speckit_bad")
    extras = [benchmark(p) for p in extra if p.is_dir()]

    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "good": good,
        "bad": bad,
        "extras": extras,
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

    print(json.dumps({"good": good["overall"], "bad": bad["overall"],
                      "bad_pitfalls": len(bad["pitfalls"]),
                      "pass": not failures}, indent=2))
    if failures:
        for f in failures:
            print(f"REGRESSION: {f}", file=sys.stderr)
        return 1
    print("benchmark gate: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
