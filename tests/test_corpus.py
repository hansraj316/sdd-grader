"""The labeled corpus evaluation passes its quality gates (issues #8, #18, #53-#57)."""

from __future__ import annotations

import importlib.util
from pathlib import Path

_BENCH = Path(__file__).resolve().parent.parent / "scripts" / "benchmark.py"


def _load_benchmark():
    spec = importlib.util.spec_from_file_location("sdd_benchmark", _BENCH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_corpus_meets_quality_gates():
    bench = _load_benchmark()
    corpus = bench.evaluate_corpus()
    assert corpus["cases"], "corpus should have cases"
    s = corpus["summary"]
    assert s["mean_recall"] >= bench.MIN_RECALL
    assert s["precision"] >= bench.MIN_PRECISION  # #56
    assert s["band_failures"] == []
    assert s["unlabeled_unexpected"] == {}  # every detection must carry a label (#56)
    assert s["false_positives_on_high_quality"] == 0
    for c in corpus["cases"]:
        assert not c["false_negatives"], f"{c['case']} missed {c['false_negatives']}"
        assert c["in_band"], f"{c['case']} score {c['overall']} outside {c['score_band']}"
        # Every case reports the richer per-case metrics.
        assert set(c) >= {
            "recall",
            "recall_incl_known_misses",
            "precision",
            "true_positives",
            "false_negatives",
            "unexpected",
            "in_band",
            "band_rationale",
        }


def test_corpus_covers_multiple_quality_levels():
    bench = _load_benchmark()
    qualities = {c["quality"] for c in bench.evaluate_corpus()["cases"]}
    assert {"high", "medium", "low"} <= qualities


def test_corpus_bands_documented_and_failable():
    """#55: every band carries a written rationale and none is so wide it can't fail."""
    bench = _load_benchmark()
    for c in bench.evaluate_corpus()["cases"]:
        assert c["band_rationale"].strip(), f"{c['case']} band has no documented rationale"
        lo, hi = c["score_band"]
        assert 0 <= lo < hi <= 100
        assert (hi - lo) < 50, f"{c['case']} band {c['score_band']} too wide to ever fail"


def test_known_misses_stay_visible_but_ungated():
    """#53: the paraphrase case documents defects lint should catch but doesn't.

    Gated recall stays 1.0 (labels are honest about current ability) while the
    honest number including known misses is < 1.0 and reported, not hidden.
    """
    bench = _load_benchmark()
    cases = {c["case"]: c for c in bench.evaluate_corpus()["cases"]}
    para = cases["paraphrased-defects"]
    assert para["known_misses_missed"], "paraphrase case should document current misses"
    assert para["recall"] == 1.0
    assert para["recall_incl_known_misses"] < 1.0
    summary = bench.evaluate_corpus()["summary"]
    assert summary["mean_recall_incl_known_misses"] < summary["mean_recall"]


def test_known_false_positive_counts_against_precision():
    """#56: the benign-lookalike known FP is in the precision denominator only."""
    bench = _load_benchmark()
    cases = {c["case"]: c for c in bench.evaluate_corpus()["cases"]}
    benign = cases["benign-lookalike"]
    assert benign["known_false_positives_detected"] == ["SPEC-AMBIGUOUS-WORDING"]
    assert benign["precision"] < 1.0
    assert benign["unexpected"] == []  # labeled, so not an unlabeled surprise
    s = bench.evaluate_corpus()["summary"]
    assert s["total_detections"] > s["correct_detections"]
    assert s["precision"] < 1.0  # honest: not reported as perfect


def test_corpus_exercises_multi_artifact_and_openspec_paths():
    """#57: labeled cases cover plan/tasks/cross-artifact checks and OpenSpec."""
    bench = _load_benchmark()
    cases = {c["case"]: c for c in bench.evaluate_corpus()["cases"]}
    xref = cases["feature-xref"]
    assert xref["adapter"] == "speckit"
    assert xref["artifact_count"] >= 4  # spec + plan + tasks + data-model
    assert {"XREF-STORY-NO-TASK", "XREF-ENTITY-NO-TASK"} <= set(xref["true_positives"])
    osc = cases["openspec-change"]
    assert osc["adapter"] == "openspec"
    assert osc["artifact_count"] >= 3  # proposal + tasks + delta spec
    assert "OPENSPEC-REQ-NO-SCENARIO" in osc["true_positives"]


def test_judge_path_golden_cases_pass():
    """#54: the offline golden-judge pipeline reproduces expected scores/mappings."""
    bench = _load_benchmark()
    judge_path = bench.evaluate_judge_path()
    s = judge_path["summary"]
    assert s["n"] >= 2, "need at least two golden judge cases"
    assert s["failures"] == []
    for c in judge_path["cases"]:
        assert c["pass"], f"{c['case']} failed checks: {c['checks']}"
        assert c["merged_overall"] == c["expected_overall"]


def test_judge_path_cleans_up_transient_judgment():
    """The runtime-written .sddgrade/judge.json never leaks into the corpus."""
    bench = _load_benchmark()
    bench.evaluate_judge_path()
    leftovers = list(bench.CORPUS.glob("*/.sddgrade/judge.json"))
    assert leftovers == []
