# Labeled spec corpus (calibration evidence)

This corpus is **separate from the unit-test fixtures**:

- `tests/fixtures/speckit_good|bad` prove the **mechanics** (the pipeline runs, the gate
  discriminates). They are not evidence of real-world accuracy.
- `corpus/cases/*` are **labeled calibration cases** — each a spec at a known quality
  level with the pitfalls a reviewer should catch and an expected score band. They let
  `scripts/benchmark.py` report recall, false positives, and score calibration, not just
  good-vs-bad separation.

Each case has `spec.md` + `expected.json`:

```json
{ "quality": "low|medium|high",
  "score_band": [min, max],
  "expect_pitfalls": ["PITFALL-ID", ...],
  "note": "why this case exists / calibration observation" }
```

## What the benchmark checks (`scripts/benchmark.py`)

- **Recall** — expected pitfalls actually caught (floor: 0.9; currently 1.0).
- **False positives** — high-quality cases (`expect_pitfalls: []`) must produce **zero**
  findings.
- **Score-band conformance** — each case's overall must land in its labeled band.

## Calibration bands (current)

| Case | Quality | Score band | Observed | Key expected pitfalls |
|------|---------|-----------:|---------:|------------------------|
| excellent | high | 95–100 | 100 | (none — clean) |
| ambiguous | medium | 80–94 | 88 | ambiguous wording, missing edge cases |
| nfr-unquantified | medium | 64–88 | 76 | NFR no threshold, non-measurable success |
| impl-leak | medium | 82–96 | 90 | impl-detail leak, speculative feature |
| clarification-gaps | low | 30–60 | 46 | unresolved clarification, placeholders, missing acceptance |

**Calibration note (#8):** the `impl-leak` case scores ~90 despite leaking a tech stack
and a speculative feature into the spec — arguably lenient versus how IBM RQA / QVscribe
would weight those. This is a known calibration gap and a candidate for future severity
re-tuning; it is captured here rather than silently accepted.

## Growing the corpus

Add real or realistic cases over time (more feature types, plan/tasks combinations,
OpenSpec changes). Keep labels honest and reviewed; widen a band only with a recorded
reason. This is the data foundation for ongoing precision/recall tracking.
