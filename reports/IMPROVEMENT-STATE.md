# SDD-Reviewer Improvement Loop — State

STATUS: ACTIVE
Iteration: 2
Last run: 2026-06-26
Open loop PRs: 1
Consecutive empty research rounds: 0

This file is the loop's only memory between runs. The loop reads it first and writes it
last. Keep it short.

## Backlog

**Canonical backlog = GitHub issues labeled `loop-candidate`** (`gh issue list --label loop-candidate --state open`).
The loop picks the highest-value open issue each run and closes it via `Closes #N` on
merge. Research rounds create new `loop-candidate` issues. The list below is a
**pre-issue idea pool** — the research phase promotes these to issues when it runs.

Research-derived items are already filed as issues **#2–#8** (passive voice, escape
clause, negative requirement, unclear actor, EARS pattern, ISO-29148 per-req judging,
score calibration).

### Idea pool (not yet issues; promote during research)

Each idea: `[ ] <id> — <what> (source)`. Mark `[~]` in-PR, `[x]` merged, `[!]` blocked.

- [~] pitfall-passive-voice — see issue #2 → PR #9 (in review)
- [ ] adapter-openspec — Add an OpenSpec adapter (change proposals + specs) behind the existing ArtifactAdapter seam; `--tool openspec` / auto-detect. (OpenSpec)
- [x] pitfall-nfr-thresholds — Detect non-functional requirements (performance/security/availability) stated without a measurable threshold. (ISO/IEC/IEEE 29148 "verifiable") → merged in #1
- [ ] pitfall-gherkin-acceptance — Deterministic check that acceptance criteria use well-formed Given/When/Then where present. (Gherkin/BDD)
- [ ] judge-invest — Judge-side INVEST scoring of user stories (independent, small, valuable, testable). (INVEST)
- [ ] checklist-ingest — Ingest a generated /speckit.checklist and score item completion. (Spec-Kit checklist)
- [ ] report-sarif — Emit SARIF so findings show up in GitHub code scanning. (CI integration practice)
- [ ] feature-rollup — Per-feature rollup scores (group artifacts by feature) in report + dashboard. (sddreview gap)
- [ ] trend-regression — Dashboard flags a score regression vs the previous run. (sddreview gap)
- [ ] constitution-crosscheck — Check that plan.md's Constitution Check references the actual principle names from constitution.md. (Spec-Kit constitution)
- [ ] fix-mode — `--fix` writes improved sections/acceptance criteria to disk (guarded). (roadmap)
- [ ] adapter-config-schema — Validate `.sddreview.toml` against a schema and warn on unknown keys. (sddreview gap)
- [ ] precommit-hook — Provide a pre-commit hook config that runs `sddreview review --rules --fail-under`. (CI/dev-loop practice)

(The loop's research phase expands this list from OpenSpec, AIDE, Canon, MAQA, Kiro,
Tessl, and Spec-Kit extensions/presets.)

## In PR

- #2 → PR #9 spec-passive-voice — SPEC-PASSIVE-VOICE pitfall + lint check (2026-06-26; awaiting CI)

## Merged

- #1 pitfall-nfr-thresholds — SPEC-NFR-NO-THRESHOLD pitfall + lint check (2026-06-25).

## Blocked

(none)

## Run log

- (seed) Loop scaffolded; backlog seeded with 12 ideas across SDD frameworks.
- iter 1 (2026-06-25, manual proof): implemented pitfall-nfr-thresholds; gate caught a
  bug (FR-001 digits counted as a threshold), fixed; pytest 22 green; benchmark PASS;
  PR #1 opened, CI green, squash-merged. Cycle validated end-to-end.
- iter 2 (2026-06-26): Phase 1 no open PRs; Phase 4 picked issue #2 (SPEC-PASSIVE-VOICE);
  implemented pitfall + lint check + 6 unit tests; pytest 28 green; benchmark good=100 bad=60.5 PASS;
  PR #9 opened; awaiting CI.
