"""The labeled corpus evaluation passes its quality gates (issues #8, #18)."""

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
    assert s["band_failures"] == []
    assert s["false_positives_on_high_quality"] == 0
    # Every case reports the richer per-case metrics.
    for c in corpus["cases"]:
        assert set(c) >= {"recall", "true_positives", "false_negatives", "unexpected", "in_band"}


def test_corpus_covers_multiple_quality_levels():
    bench = _load_benchmark()
    qualities = {c["quality"] for c in bench.evaluate_corpus()["cases"]}
    assert {"high", "medium", "low"} <= qualities
