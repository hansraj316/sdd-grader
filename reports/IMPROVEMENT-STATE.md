# SDD-Grader Improvement Loop — State

STATUS: ACTIVE
Iteration: 6
Last run: 2026-06-29 (manual batch — cleared the open backlog)
Open loop PRs: 0
Consecutive empty research rounds: 0

> Manual batch on 2026-06-29 merged PR #12 (#5) and then shipped #6, #7, #8, #13, #14,
> #15, #16, #17, #18, #19, #20 as PRs #21–#28 (all CI-green, squash-merged). No open
> `loop-candidate` issues remain. The loop's next run should do Phase 0–1 and, finding
> the backlog empty, run a research round (Phase 3) to refill it — or set
> STATUS: NOTHING-TO-IMPROVE after two empty rounds.

This file is the loop's only memory between runs. The loop reads it first and writes it
last. Keep it short.

## Backlog

**Canonical backlog = GitHub issues labeled `loop-candidate`** (`gh issue list --label loop-candidate --state open`).
The loop picks the highest-value open issue each run and closes it via `Closes #N` on
merge. Research rounds create new `loop-candidate` issues. The list below is a
**pre-issue idea pool** — the research phase promotes these to issues when it runs.

Research-derived items are already filed as issues **#3–#8** (escape clause, negative
requirement, unclear actor, EARS pattern, ISO-29148 per-req judging, score calibration).

### Idea pool (not yet issues; promote during research)

Each idea: `[ ] <id> — <what> (source)`. Mark `[~]` in-PR, `[x]` merged, `[!]` blocked.

- [x] pitfall-escape-clause — see issue #3 → merged in PR #10
- [~] pitfall-negative-requirement — see issue #4 → PR #11 (in review)
- [ ] adapter-openspec — Add an OpenSpec adapter (change proposals + specs) behind the existing ArtifactAdapter seam; `--tool openspec` / auto-detect. (OpenSpec)
- [x] pitfall-nfr-thresholds — Detect non-functional requirements (performance/security/availability) stated without a measurable threshold. (ISO/IEC/IEEE 29148 "verifiable") → merged in #1
- [x] pitfall-passive-voice — SPEC-PASSIVE-VOICE pitfall + lint check → merged in #9
- [ ] pitfall-gherkin-acceptance — Deterministic check that acceptance criteria use well-formed Given/When/Then where present. (Gherkin/BDD)
- [ ] judge-invest — Judge-side INVEST scoring of user stories (independent, small, valuable, testable). (INVEST)
- [ ] checklist-ingest — Ingest a generated /speckit.checklist and score item completion. (Spec-Kit checklist)
- [ ] report-sarif — Emit SARIF so findings show up in GitHub code scanning. (CI integration practice)
- [ ] feature-rollup — Per-feature rollup scores (group artifacts by feature) in report + dashboard. (sddgrade gap)
- [ ] trend-regression — Dashboard flags a score regression vs the previous run. (sddgrade gap)
- [ ] constitution-crosscheck — Check that plan.md's Constitution Check references the actual principle names from constitution.md. (Spec-Kit constitution)
- [ ] fix-mode — `--fix` writes improved sections/acceptance criteria to disk (guarded). (roadmap)
- [ ] adapter-config-schema — Validate `.sddgrade.toml` against a schema and warn on unknown keys. (sddgrade gap)
- [ ] precommit-hook — Provide a pre-commit hook config that runs `sddgrade review --rules --fail-under`. (CI/dev-loop practice)

(The loop's research phase expands this list from OpenSpec, AIDE, Canon, MAQA, Kiro,
Tessl, and Spec-Kit extensions/presets.)

## In PR

- #5 → PR #12 spec-unclear-actor — SPEC-UNCLEAR-ACTOR pitfall + lint check (2026-06-29; awaiting CI)

## Merged

- #1 pitfall-nfr-thresholds — SPEC-NFR-NO-THRESHOLD pitfall + lint check (2026-06-25).
- #2 → PR #9 pitfall-passive-voice — SPEC-PASSIVE-VOICE pitfall + lint check (2026-06-27).
- #3 → PR #10 pitfall-escape-clause — SPEC-ESCAPE-CLAUSE pitfall + lint check (2026-06-28).
- #4 → PR #11 spec-negative-requirement — SPEC-NEGATIVE-REQUIREMENT pitfall + lint check (2026-06-29, CI was green).

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
- iter 3 (2026-06-27): Phase 1 merged PR #9 (SPEC-PASSIVE-VOICE, issue #2 closed, CI was green);
  Phase 4 picked issue #3 (SPEC-ESCAPE-CLAUSE); added pitfall to catalog with 11 escape-clause
  patterns + 9 unit tests; pytest 37 green; benchmark good=100 bad=60.5 PASS; PR #10 opened.
- iter 4 (2026-06-28): Phase 1 merged PR #10 (SPEC-ESCAPE-CLAUSE, issue #3 auto-closed, CI was green);
  Phase 4 picked issue #4 (SPEC-NEGATIVE-REQUIREMENT); dedicated lint check + 8 unit tests;
  pytest 45 green; benchmark good=100 bad=60.5 PASS; PR #11 opened.
- iter 5 (2026-06-29): Phase 1 merged PR #11 (SPEC-NEGATIVE-REQUIREMENT, issue #4 auto-closed, CI was green);
  Phase 4 picked issue #5 (SPEC-UNCLEAR-ACTOR); pronoun-subject + subjectless-requirement lint check + 10 unit tests;
  pytest 55 green; benchmark good=100 bad=60.5 PASS; PR #12 opened.
