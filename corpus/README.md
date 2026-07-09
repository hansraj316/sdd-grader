# Labeled spec corpus (calibration evidence)

This corpus is **separate from the unit-test fixtures**:

- `tests/fixtures/speckit_good|bad` prove the **mechanics** (the pipeline runs, the gate
  discriminates). They are not evidence of real-world accuracy.
- `corpus/cases/*` are **labeled calibration cases** — each a case at a known quality
  level with the pitfalls a reviewer should catch and an expected score band. They let
  `scripts/benchmark.py` report recall, precision, and score calibration, not just
  good-vs-bad separation.

A case is either a single top-level `spec.md`, or a **full feature tree** (#57) —
`specs/<id>/spec.md|plan.md|tasks.md|data-model.md` for Spec-Kit, or an `openspec/`
change directory for OpenSpec. Multi-file cases are routed through the same adapter
discovery the CLI uses, so the corpus and real reviews exercise identical code.

## Corpus methodology (#53): how cases are authored

The original five cases were written *from* the rubric's own trigger words, which makes
recall on them a regex self-consistency check, not detection evidence. They are kept —
labeled as such in their notes — as regex unit tests, and the corpus now also contains
cases authored **without looking at the pattern lists**:

- **`paraphrased-defects`** — the same defect classes as `ambiguous` / `nfr-unquantified` /
  `impl-leak`, expressed in wording that avoids the catalog's regexes ("snappy",
  "could later grow", "CockroachDB"). Defects lint *should* ideally catch but currently
  misses are labeled `known_misses`: excluded from the gated recall (labels stay honest
  about current ability) but reported in `recall_incl_known_misses` so the gap is
  visible in every report instead of hidden.
- **`benign-lookalike`** — a genuinely good spec that deliberately contains
  trigger-adjacent prose in benign contexts ("simple" / "faster" in Out of Scope,
  "latency" with a threshold, "scalable" bounded to a number). Its one wrong detection
  is labeled `known_false_positives`: it counts **against** precision but is exempt from
  the unlabeled-detection gate, so the metric is honest while the gate passes.
- **`realworld-mcp-proxy`** — adapts the flawed spec shape observed in real Spec-Kit
  repos (the polymarket-kit MCP-server spec pattern): a `[NEEDS CLARIFICATION]` marker
  left inside an FR, the template's `$ARGUMENTS` input line retained, a leaked API
  style, and a fully-unchecked Review & Acceptance Checklist.

Labeling rule: label a case **before** looking at the tool's output where possible, and
record disagreements in the `note`. When the engine finds something real that the label
missed, promote it to `accepted_extras` (it is correct — it just wasn't the case's
point) rather than silently editing `expect_pitfalls`.

## `expected.json` schema

```json
{ "quality": "low|medium|high",
  "score_band": [min, max],
  "band_rationale": "why THIS band — what makes the case low/medium/high (#55)",
  "expect_pitfalls": ["..."],          // must be detected; a miss is a gated false negative
  "accepted_extras": ["..."],          // genuine defects beyond the case's point; count as correct
  "known_misses": ["..."],             // lint SHOULD catch these but currently doesn't (#53)
  "known_false_positives": ["..."],    // wrong-but-current detections; count against precision (#56)
  "note": "why this case exists / calibration observation" }
```

Any detection outside all four lists is **unlabeled** and fails the gate: new rules may
not spray findings over the corpus without someone classifying each one as correct
(`accepted_extras`) or wrong (`known_false_positives`).

## What the benchmark checks (`scripts/benchmark.py`)

- **Recall** — labeled expected pitfalls actually caught (floor: 0.9; currently 1.0).
  The honest companion number `recall_incl_known_misses` (currently 0.92) includes the
  documented misses and is reported, not gated.
- **Precision (#56)** — labeled-correct detections / all detections, micro-averaged
  (floor: 0.95; measured 0.958 when the gate was introduced — the one uncredited
  detection is the labeled known-FP on `benign-lookalike`). One new unlabeled or
  known-FP detection anywhere in the corpus trips the floor.
- **Unlabeled detections** — must be zero on every case (not just the high-quality
  negative controls).
- **Score-band conformance** — each case's overall must land in its labeled band; every
  band has a written `band_rationale` and no band is wide enough to be unfailable.
- **Judge path (#54)** — `judge.golden.json` fixtures (hand-authored raw judge output +
  expectations) are pushed through the *real* agent-judge pipeline offline: the
  benchmark generates the artifact hash manifest at runtime (content hashes must match
  disk), writes a transient `.sddgrade/judge.json`, and asserts the merged score,
  judge-pitfall set, artifact attribution (relative path / unique basename /
  unattributed bucket), and enum normalization ("major" → high, "traceable" →
  traceability). This gates the judge half deterministically, without an API key.

## Score bands (#55): how they were derived

Bands are re-derived from the current engine's measured output, then adjusted only with
a written justification (see each case's `band_rationale`). Two deliberate deviations
from "fit the current number":

- `impl-leak`'s floor is widened **down** to 65 because external judgment (IBM RQA /
  QVscribe weighting; the case's own leniency note) says the spec deserves ~65-80 while
  the engine scores 90 — so the tracked severity re-tuning *passes* the gate when it
  lands instead of being blocked by it.
- `benign-lookalike`'s ceiling is 100 so *fixing* its labeled false positive passes.

| Case | Quality | Score band | Observed | Key labels |
|------|---------|-----------:|---------:|------------|
| excellent | high | 95–100 | 100 | (none — clean negative control) |
| benign-lookalike | high | 90–100 | 94 | known FP: ambiguous-wording on quantified "scalable" |
| ambiguous | medium | 75–92 | 88 | ambiguous wording, missing edge cases |
| paraphrased-defects | medium | 55–92 | 88 | non-measurable success; 4 known misses |
| feature-xref | medium | 84–96 | 91.7 | story→task + entity→task traceability, plan marker |
| openspec-change | medium | 86–97 | 93.6 | requirement without scenario, ambiguous wording |
| impl-leak | medium | 65–92 | 90 | impl-detail leak, speculative feature (+ compound FR) |
| nfr-unquantified | medium | 60–84 | 76 | NFR no threshold, non-measurable success (+ vague wording) |
| clarification-gaps | low | 30–60 | 46 | unresolved clarification, placeholders, missing acceptance |
| realworld-mcp-proxy | low | 50–70 | 64 | unresolved marker in FR, `$ARGUMENTS` residue, leaked API style |

**Calibration note (#8/#55):** `impl-leak` still scores ~90 despite leaking a tech stack —
lenient versus how IBM RQA / QVscribe would weight it. That gap is now encoded in the
band floor (65) rather than fitted away, so closing it is gate-compatible tracked work.

## Growing the corpus

Add real or realistic cases over time (more feature types, more full feature trees,
OpenSpec changes, more golden judge fixtures). Keep labels honest and reviewed; change a
band only with a recorded reason in `band_rationale`. Prefer paraphrased/real-world
authorship over rubric-derived wording — the corpus should measure detection, not regex
self-consistency.
