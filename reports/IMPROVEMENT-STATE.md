# SDD-Grader Improvement Loop — State

STATUS: ACTIVE
Iteration: 14
Last run: 2026-07-07
Open loop PRs: 1
Consecutive empty research rounds: 0

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
- [x] pitfall-negative-requirement — see issue #4 → merged in PR #11
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

- #46 → PR #74 remove-dead-config-keys — delete Config.integration + Config.rubric_override; scaffold tool=auto (2026-07-07; awaiting CI)

## Merged

- #1 pitfall-nfr-thresholds — SPEC-NFR-NO-THRESHOLD pitfall + lint check (2026-06-25).
- #2 → PR #9 pitfall-passive-voice — SPEC-PASSIVE-VOICE pitfall + lint check (2026-06-27).
- #3 → PR #10 pitfall-escape-clause — SPEC-ESCAPE-CLAUSE pitfall + lint check (2026-06-28).
- #4 → PR #11 spec-negative-requirement — SPEC-NEGATIVE-REQUIREMENT pitfall + lint check (2026-06-29, CI was green).
- #5 → PR #12/#33-batch spec-unclear-actor — SPEC-UNCLEAR-ACTOR pitfall + lint check (2026-06-29, CI was green; merged in manual batch).
- #29 → PR #33 json-warnings-to-stderr — route judge-unavailable warning to stderr in --json mode (2026-07-01, CI was green; squash-merged).
- #30 → PR #34 fix-malformed-judge-json — handle malformed judge.json without crashing (2026-07-02, CI was green; squash-merged).
- #43 → PR #70 dedup-judge-findings — dedup 'both'-method pitfall findings at lint+judge merge (2026-07-04, CI was green; squash-merged).
- #69 → PR #71 template-aware-lint — phantom clarification markers + sibling acceptance sections (2026-07-05, CI was green; squash-merged).
- #31 → PR #72 fix-cli-tool-default — Optional[Tool] default None in cli.py; Config.tool default "speckit"→"auto" (2026-07-06, CI was green; squash-merged).
- #44 → PR #73 fix-xref-entity-false-positives — _STRUCTURAL_HEADINGS denylist + word-boundary entity matching (2026-07-07, CI was green; squash-merged).

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
- iter 6 (2026-06-29, manual batch): merged PR #12 and shipped PRs #21–#32 (issues #6–#28);
  backlog cleared; 0 open loop-candidate issues remain at close of batch.
- iter 7 (2026-06-30): Phase 1 no open loop/* PRs; Phase 2 found 3 open loop-candidate issues
  (#29, #30, #31 — all bugs filed by prior batch); Phase 4 picked #29 (--json warning on stdout);
  route warn_console to stderr when json_out=True; 2 regression tests; pytest 92 green;
  benchmark good=100 bad=60.5 PASS; PR #33 opened.
- iter 8 (2026-07-01): Phase 1 merged PR #33 (issue #29 closed, CI was green); Phase 4 picked
  #30 (malformed judge.json crash); fixed agent.py isinstance check before data.get() and added
  TypeError to judge.py to_findings() except clause; 4 regression tests; pytest 96 green;
  benchmark good=100 bad=60.5 PASS; PR #34 opened.
- iter 9 (2026-07-02): Phase 1 merged PR #34 (issue #30 closed, CI was green); Phase 4 picked
  #31 (CLI --tool default overrides .sddreview.toml); changed cli.py tool default None→None and
  config.py Config.tool default "speckit"→"auto"; 4 regression tests; pytest 100 green;
  benchmark good=100 bad=60.5 PASS; PR #35 opened.
- iter 10 (2026-07-03): Phase 0 synced (37 commits ahead; sddreview→sddgrade rename + many
  new features merged); Phase 1 no open loop/* PRs (PR #35 appears merged by manual batch;
  issue #31 still open); Phase 2 found 23 open loop-candidate issues; Phase 4 picked #43
  (lint+judge double-count 'both'-method pitfalls); added dedup in runner.py before
  findings.extend(); 3 regression tests; pytest 142 green; benchmark good=100 bad=61 PASS;
  PR #70 opened; issue #43 commented.
- iter 11 (2026-07-04): Phase 1 merged PR #70 (issue #43 closed, CI was green; squash-merged
  via MCP); Phase 2 found 22 open loop-candidate issues; Phase 4 picked #69 (phantom
  SPEC-UNRESOLVED-CLARIFICATION on blockquote template lines + SPEC-MISSING-ACCEPTANCE
  missing sibling acceptance sections); added _count_real_clarification_markers() helper
  + expanded acceptance scan to sibling sections; 9 regression tests; pytest 152 green;
  benchmark good=100 bad=61 PASS; PR #71 opened via MCP (git push 503'd); issue #69 commented.
- iter 12 (2026-07-05): Phase 1 merged PR #71 (issue #69 closed, CI was green; squash-merged
  via MCP); PR #35 closed (irrecoverable conflicts from sddreview→sddgrade rename); Phase 2
  found 21 open loop-candidate issues; Phase 4 picked #31 (CLI --tool default overrides
  .sddgrade.toml); changed cli.py tool default to Optional[Tool]=None + config.py Config.tool
  default "speckit"→"auto"; 5 regression tests; pytest 157 green; benchmark good=100 bad=61
  PASS; PR #72 opened via MCP (git push 503'd); issue #31 commented.
- iter 13 (2026-07-06): Phase 1 merged PR #72 (issue #31 closed, CI was green; converted draft
  → ready + squash-merged via MCP); Phase 2 found 20 open loop-candidate issues; Phase 4 picked
  #44 (XREF-ENTITY-NO-TASK false positives on structural headings); added _STRUCTURAL_HEADINGS
  denylist + _entity_word_re() word-boundary cache in lint.py; 7 regression tests; pytest 164
  green; benchmark good=100 bad=61 PASS; PR #73 opened via MCP (git push 503'd); issue #44
  commented.
- iter 14 (2026-07-07): Phase 1 merged PR #73 (issue #44 closed, CI was green; converted draft
  → ready + squash-merged via MCP); Phase 2 found 19 open loop-candidate issues; Phase 4 picked
  #46 (Config.integration + Config.rubric_override parsed but never used; scaffolded config writes
  tool="speckit" not "auto"); deleted both dead Config fields + their load() branches; fixed
  _default_config() to emit tool="auto" + drop integration key; 5 regression tests; pytest 169
  green; benchmark good=100 bad=61 PASS; PR #74 opened via MCP (git push 503'd); issue #46
  commented.
