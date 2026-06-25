# SDD-Reviewer Improvement Loop — State

STATUS: ACTIVE
Iteration: 1
Last run: 2026-06-25 (manual proof run during build)
Open loop PRs: 0
Consecutive empty research rounds: 0

This file is the loop's only memory between runs. The loop reads it first and writes it
last. Keep it short.

## Backlog (actionable ideas — highest value first)

Each idea: `[ ] <id> — <what> (source)`. Mark `[~]` in-PR, `[x]` merged, `[!]` blocked.

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
- [ ] pitfall-passive-voice — Detect requirements in passive voice / with no clear actor ("shall be able to be ..."). (IBM RQA issue taxonomy / INCOSE)
- [ ] pitfall-escape-clause — Detect escape/loophole clauses in requirements ("if possible", "where feasible", "as appropriate"). (IBM RQA / Requirements Smells)
- [ ] pitfall-negative-requirement — Flag requirements stated negatively ("shall not ..."), which are hard to verify. (IBM RQA)
- [ ] pitfall-unclear-actor — Flag requirements with no identifiable subject/actor. (IBM RQA / ISO 29148 unambiguous)
- [ ] check-ears-pattern — Optional check that functional requirements follow an EARS-style pattern (When/While/Where/If ... the system shall ...). (QVscribe / EARS)
- [ ] judge-iso29148-perreq — Judge-side per-requirement scoring on ISO/IEC/IEEE 29148 characteristics (singular, complete, correct). (ISO/IEC/IEEE 29148; cf. QVscribe 5-pt, RQA 11-score)
- [ ] score-calibration — Compare sddreview scores against IBM RQA / QVscribe-style per-requirement scoring as a calibration benchmark. (competitive analysis)

(The loop's research phase expands this list from OpenSpec, AIDE, Canon, MAQA, Kiro,
Tessl, and Spec-Kit extensions/presets.)

## In PR

(none)

## Merged

- #1 pitfall-nfr-thresholds — SPEC-NFR-NO-THRESHOLD pitfall + lint check (2026-06-25).

## Blocked

(none)

## Run log

- (seed) Loop scaffolded; backlog seeded with 12 ideas across SDD frameworks.
- iter 1 (2026-06-25, manual proof): implemented pitfall-nfr-thresholds; gate caught a
  bug (FR-001 digits counted as a threshold), fixed; pytest 22 green; benchmark PASS;
  PR #1 opened, CI green, squash-merged. Cycle validated end-to-end.
