# SDD-Grader Improvement Loop — State

STATUS: ACTIVE
Iteration: 29
Last run: 2026-07-22
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
- [x] pitfall-gherkin-acceptance — Deterministic check that acceptance criteria use well-formed Given/When/Then where present. (Gherkin/BDD) → issue #78 → merged in PR #82
- [x] adapter-config-schema — Validate `.sddgrade.toml` against a schema and warn on unknown keys. (sddgrade gap) → issue #80 → merged in PR #84
- [x] constitution-crosscheck — Cross-artifact check: plan.md's Constitution Check must reference actual principle names from constitution.md → issue #79 → merged in PR #85
- [x] precommit-hook — Provide a pre-commit hook config that runs `sddgrade review --rules --fail-under`. (CI/dev-loop practice) → issue #81 → PR #86 → merged 2026-07-14
- [ ] judge-invest — Judge-side INVEST scoring of user stories (independent, small, valuable, testable). (INVEST)
- [ ] checklist-ingest — Ingest a generated /speckit.checklist and score item completion. (Spec-Kit checklist)
- [ ] report-sarif — Emit SARIF so findings show up in GitHub code scanning. (CI integration practice)
- [ ] feature-rollup — Per-feature rollup scores (group artifacts by feature) in report + dashboard. (sddgrade gap)
- [ ] trend-regression — Dashboard flags a score regression vs the previous run. (sddgrade gap)
- [ ] fix-mode — `--fix` writes improved sections/acceptance criteria to disk (guarded). (roadmap)
- [x] story-no-benefit — SPEC-STORY-NO-BENEFIT pitfall: "As a X, I want Y" without "so that Z" clause. (INVEST Valuable, Connextra, ISO 29148) → issue #87 → PR #90 → merged 2026-07-15
- [x] unbounded-scope — REQ-UNBOUNDED-SCOPE pitfall: "etc.", "and so on" in requirements. (ISO 29148, QVscribe) → issue #88 → PR #91 → merged 2026-07-16
- [x] plan-missing-rollback — PLAN-MISSING-ROLLBACK pitfall: plan.md with no rollback/revert/fallback mention. (Spec-Kit, ISO 25010) → issue #89 → PR #92 → merged 2026-07-17
- [x] req-duplicate-id — REQ-DUPLICATE-ID pitfall: same FR/NFR/AC/US identifier on multiple lines. (ISO 29148, QVscribe) → issue #93 → PR #96 → merged 2026-07-18
- [x] plan-no-testing-strategy — PLAN-NO-TESTING-STRATEGY pitfall + _plan_no_testing_strategy() helper; _PHASE_HEADING_RE + _TESTING_VOCAB_RE constants; 2-phase guard prevents false positives on short plans; 13 unit tests; pytest 403 green; benchmark good=100 bad=61 PASS → issue #94 → PR #97 → merged 2026-07-19
- [x] plan-missing-observability — PLAN-MISSING-OBSERVABILITY pitfall + _plan_missing_observability() helper; _OBSERVABILITY_RE constant; reuses _DEPLOY_VOCAB_RE/_DEPLOY_SECTION_RE guard; fires on monitoring/logging/metrics/alerting/SLO/SLA absence; 14 unit tests; pytest 417 green; benchmark good=100 bad=61 PASS → issue #95 → PR #98 → merged 2026-07-20
- [x] req-weak-directive — REQ-WEAK-DIRECTIVE pitfall + _weak_directive() helper; _WEAK_MODAL_RE/_MANDATORY_MODAL_RE/_STRICT_REQ_ID_LINE_RE constants; _strict_req_mask() scopes to section+label only (avoids false positives on prose "should"); 14 unit tests; pytest 431 green; benchmark good=100 bad=61 precision=0.966 PASS → issue #99 → PR #102 → merged 2026-07-21
- [x] plan-missing-security — PLAN-MISSING-SECURITY pitfall + _plan_missing_security() helper; _SECURITY_RE constant; reuses _DEPLOY_VOCAB_RE/_DEPLOY_SECTION_RE guard; fires on auth/TLS/encrypt/secrets/RBAC/IAM/firewall/vault absence; 17 unit tests; pytest 448 green; benchmark good=100 bad=59.2 PASS → issue #100 → PR #103 → merged 2026-07-22
- [~] spec-pronoun-antecedent — SPEC-PRONOUN-ANTECEDENT; object pronouns (it/them/their/this/that/these/those) after modal verb; _VAGUE_SUBJECT_RE guard avoids double-count with SPEC-UNCLEAR-ACTOR; possessive 'its' excluded; 15 unit tests; pytest 463 green; benchmark good=100 bad=58.6 precision=0.968 PASS (2026-07-22; awaiting CI) → issue #101 → PR #104

(The loop's research phase expands this list from OpenSpec, AIDE, Canon, MAQA, Kiro,
Tessl, and Spec-Kit extensions/presets.)

## In PR

- #101 → PR #104 spec-pronoun-antecedent — SPEC-PRONOUN-ANTECEDENT pitfall + _pronoun_antecedent() helper; _PRONOUN_ANTECEDENT_RE; 15 unit tests; pytest 463 green; benchmark good=100 bad=58.6 precision=0.968 PASS (2026-07-22; awaiting CI)

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
- #46 → PR #74 remove-dead-config-keys — delete Config.integration + Config.rubric_override; scaffold tool=auto (2026-07-08, CI was green; squash-merged).
- #48 → PR #77 adapter-structural-seam — add structural_checks/cross_artifact_checks/hint to ArtifactAdapter protocol; moved _openspec_structural to OpenSpecAdapter; removed adapter.name branching from lint() (2026-07-10, CI was green; squash-merged).
- #78 → PR #82 gherkin-malformed-ac — SPEC-GHERKIN-MALFORMED-AC pitfall + lint check; formal Gherkin mode (≥2 leading keywords) guard prevents false positives on inline prose ACs (2026-07-11, CI was green; squash-merged).
- #80 → PR #84 config-unknown-key-warning — warn on stderr for unrecognised keys in .sddgrade.toml; also warns on unknown dimension names in [weights] sub-table (2026-07-12, CI was green; squash-merged).
- #79 → PR #85 constitution-crosscheck — SPECKIT-CONSTITUTION-CROSSCHECK cross-artifact lint check; _constitution_principles() helper filters placeholders/generic headings; moved before tasks guard; 12 unit tests (2026-07-13, CI was green; squash-merged).
- #81 → PR #86 precommit-hook — .pre-commit-hooks.yaml at repo root; hook runs sddgrade review --rules --fail-under 60 on specs/*.md + openspec/*.md; README "Pre-commit integration" section; 8 unit tests (2026-07-14, CI was green; squash-merged).
- #87 → PR #90 story-no-benefit — SPEC-STORY-NO-BENEFIT pitfall + _story_no_benefit() lint check; 10 unit tests; 3 corpus expected.json accepted_extras (2026-07-15, CI was green; squash-merged).
- #88 → PR #91 unbounded-scope — REQ-UNBOUNDED-SCOPE pitfall + _unbounded_scope() lint check; 12 unit tests; applies to spec + plan (2026-07-16, CI was green; squash-merged).
- #89 → PR #92 plan-missing-rollback — PLAN-MISSING-ROLLBACK pitfall + _plan_missing_rollback() helper; _ROLLBACK_RE/_DEPLOY_VOCAB_RE/_DEPLOY_SECTION_RE constants; deploy-guard prevents false positives on refactoring plans; silent on any rollback keyword; 13 unit tests; pytest 377 green; benchmark good=100 bad=61 PASS (2026-07-17, CI was green; squash-merged).
- #93 → PR #96 req-duplicate-id — REQ-DUPLICATE-ID pitfall + _req_duplicate_id() helper; _REQ_ID_RE constant; fenced-block exclusion via _fence_mask(); case-insensitive; fires once per artifact; 13 unit tests; pytest 390 green; benchmark good=100 bad=61 PASS (2026-07-18, CI was green; squash-merged).
- #94 → PR #97 plan-no-testing-strategy — PLAN-NO-TESTING-STRATEGY pitfall + _plan_no_testing_strategy() helper; _PHASE_HEADING_RE + _TESTING_VOCAB_RE constants; 2-phase guard prevents false positives on short plans; 13 unit tests; pytest 403 green; benchmark good=100 bad=61 PASS (2026-07-19, CI was green; squash-merged).
- #95 → PR #98 plan-missing-observability — PLAN-MISSING-OBSERVABILITY pitfall + _plan_missing_observability() helper; _OBSERVABILITY_RE constant; reuses _DEPLOY_VOCAB_RE/_DEPLOY_SECTION_RE guard; 14 unit tests; pytest 417 green; benchmark good=100 bad=61 PASS (2026-07-20, CI was green; squash-merged).
- #99 → PR #102 req-weak-directive — REQ-WEAK-DIRECTIVE pitfall + _weak_directive() helper; _WEAK_MODAL_RE/_MANDATORY_MODAL_RE/_STRICT_REQ_ID_LINE_RE constants; _strict_req_mask(); 14 unit tests; pytest 431 green; benchmark good=100 bad=61 PASS (2026-07-21, CI was green; squash-merged).
- #100 → PR #103 plan-missing-security — PLAN-MISSING-SECURITY pitfall + _plan_missing_security() helper; _SECURITY_RE; 17 unit tests; pytest 448 green; benchmark good=100 bad=59.2 PASS (2026-07-22, CI was green; squash-merged).

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
- iter 15 (2026-07-08): Phase 1 merged PR #74 (issue #46 closed, CI was green; converted draft
  → ready + squash-merged via MCP); Phase 2 found 18 open loop-candidate issues; Phase 4 picked
  #49 (judge prompt injection — artifact content inlined into prompt with no data/instruction
  boundary); wrapped each artifact in <artifact_data path="..." type="..."> block + added
  "DATA only" framing instruction in build_prompt(); added security note to judge-command.md;
  updated test_judge_fixes.py + 6 new regression tests; pytest 175 green; benchmark good=100
  bad=61 PASS; PR #75 opened; issue #49 commented.
- iter 16 (2026-07-09): Phase 1: PR #75 (judge-prompt-injection-guard) found closed/not-merged —
  issue #49 already closed via batch PR #76; 0 open loop/* PRs. Phase 2 found 1 open
  loop-candidate issue (#48 — lint engine hard-codes adapter names + hosts toolchain-specific
  checks). Phase 4 picked #48; added structural_checks/cross_artifact_checks/hint to
  ArtifactAdapter protocol; moved _openspec_structural to OpenSpecAdapter.structural_checks;
  removed adapter.name branching from lint(); fixed no-artifacts + missing-section messages to
  use adapter.name/hint; 15 new regression tests; pytest 261 green; benchmark good=100 bad=61
  PASS; PR #77 opened; issue #48 commented.
- iter 17 (2026-07-10): Phase 1 merged PR #77 (issue #48 closed, CI was green; converted draft
  → ready + squash-merged via MCP). Phase 2 found 0 open loop-candidate issues → Phase 3:
  filed 4 new issues (#78 pitfall-gherkin-acceptance, #79 constitution-crosscheck, #80
  adapter-config-schema, #81 precommit-hook). Phase 4 picked #78 (SPEC-GHERKIN-MALFORMED-AC
  — formal Gherkin check requiring ≥2 line-leading keywords to avoid false positives on
  inline prose ACs); 3 regexes + check in _spec_checks + 16 unit tests; pytest 277 green;
  benchmark good=100 bad=61 PASS; PR #82 opened; issue #78 commented.
- iter 18 (2026-07-11): Phase 1 merged PR #82 (issue #78 closed, CI was green; converted draft
  → ready + squash-merged via MCP). Phase 2 found 3 open loop-candidate issues (#79, #80, #81);
  Phase 4 picked #80 (warn on unknown .sddgrade.toml keys); added _warn_unknown_keys() +
  _KNOWN_KEYS + _VALID_DIMENSIONS in config.py; 7 unit tests; pytest 322 green; benchmark
  good=100 bad=61 PASS; PR #84 opened; issue #80 commented.
- iter 19 (2026-07-12): Phase 1 merged PR #84 (issue #80 closed, CI was green; squash-merged).
  Phase 2 found 2 open loop-candidate issues (#79, #81); Phase 4 picked #79 (SPECKIT-CONSTITUTION-CROSSCHECK
  — plan.md Constitution Check must reference actual principle names from constitution.md);
  added SPECKIT-CONSTITUTION-CROSSCHECK pitfall + _constitution_principles() helper + moved
  check before tasks-guard in _cross_artifact(); 12 unit tests; pytest 334 green; benchmark
  good=100 bad=61 PASS; PR #85 opened (draft); issue #79 commented.
- iter 20 (2026-07-13): Phase 1 merged PR #85 (issue #79 closed, CI was green; converted draft
  → ready + squash-merged via MCP). Phase 2 found 1 open loop-candidate issue (#81 pre-commit
  hook); Phase 4 picked #81; added .pre-commit-hooks.yaml (id: sddgrade; --rules --fail-under 60;
  files: specs/*.md + openspec/*.md; pass_filenames: false) + README "Pre-commit integration"
  section + 8 unit tests; pytest 342 green; benchmark good=100 bad=61 PASS; PR #86 opened
  (draft); issue #81 commented.
- iter 21 (2026-07-14): Phase 1 merged PR #86 (issue #81 closed, CI was green; converted draft
  → ready + squash-merged via MCP). Phase 2 found 0 open loop-candidate issues → Phase 3:
  filed 3 new issues (#87 story-no-benefit, #88 unbounded-scope, #89 plan-missing-rollback).
  Phase 4 picked #87 (SPEC-STORY-NO-BENEFIT — Connextra user story missing "so that" clause);
  added pitfall + _story_no_benefit() helper + 3 regex constants; 10 unit tests; updated 3
  corpus expected.json accepted_extras; pytest 352 green; benchmark good=100 bad=61 PASS;
  PR #90 opened (draft); issue #87 commented.
- iter 22 (2026-07-15): Phase 1 merged PR #90 (issue #87 closed, CI was green; converted draft
  → ready + squash-merged via MCP). Phase 2 found 2 open loop-candidate issues (#88, #89);
  Phase 4 picked #88 (REQ-UNBOUNDED-SCOPE — open-ended enumerations in requirement lines);
  added pitfall + _unbounded_scope() helper + _UNBOUNDED_SCOPE_RE + _REQ_BROAD_RE constants;
  12 unit tests; pytest 364 green; benchmark good=100 bad=15 PASS; PR #91 opened (draft);
  issue #88 commented.
- iter 23 (2026-07-16): Phase 1 merged PR #91 (issue #88 closed, CI was green; converted draft
  → ready + squash-merged via MCP). Phase 2 found 1 open loop-candidate issue (#89); Phase 4
  picked #89 (PLAN-MISSING-ROLLBACK — deployment plans with no rollback/revert/fallback mention);
  added pitfall + _plan_missing_rollback() helper + _ROLLBACK_RE/_DEPLOY_VOCAB_RE/_DEPLOY_SECTION_RE
  constants; guard prevents false positives on pure-refactoring plans; 13 unit tests; pytest 377
  green; benchmark good=100 bad=61 PASS; PR #92 opened (draft); issue #89 commented.
- iter 24 (2026-07-17): Phase 1 merged PR #92 (issue #89 closed, CI was green; converted draft → ready + squash-merged). Phase 2 found 0 open loop-candidate issues → Phase 3: filed 3 new issues (#93 req-duplicate-id, #94 plan-no-testing-strategy, #95 plan-missing-observability). Phase 4 picked #93 (REQ-DUPLICATE-ID — same FR/NFR/AC/US identifier on multiple non-fenced lines); added pitfall + _req_duplicate_id() helper + _REQ_ID_RE constant; case-insensitive; fenced-block exclusion via _fence_mask(); fires once per artifact; 13 unit tests; pytest 390 green; benchmark good=100 bad=61 PASS; PR #96 opened (draft); issue #93 commented.
- iter 25 (2026-07-18): Phase 1 merged PR #96 (issue #93 closed, CI was green; converted draft → ready + squash-merged via MCP). Phase 2 found 2 open loop-candidate issues (#94, #95); Phase 4 picked #94 (PLAN-NO-TESTING-STRATEGY — multi-phase plan with no testing vocabulary); added pitfall + _plan_no_testing_strategy() helper + _PHASE_HEADING_RE + _TESTING_VOCAB_RE constants; 2-phase guard prevents false positives on short plans; 13 unit tests; pytest 403 green; benchmark good=100 bad=61 PASS; PR #97 opened (draft); issue #94 commented.
- iter 26 (2026-07-19): Phase 1 merged PR #97 (issue #94 closed, CI was green; converted draft → ready + squash-merged via MCP). Phase 2 found 1 open loop-candidate issue (#95); Phase 4 picked #95 (PLAN-MISSING-OBSERVABILITY — deployment plans with no monitoring/logging/metrics/alerting mention); added pitfall + _plan_missing_observability() helper + _OBSERVABILITY_RE constant; reuses _DEPLOY_VOCAB_RE/_DEPLOY_SECTION_RE guard; 14 unit tests; pytest 417 green; benchmark good=100 bad=61 PASS; PR #98 opened (draft); issue #95 commented.
- iter 27 (2026-07-20): Phase 1 merged PR #98 (issue #95 closed, CI was green; converted draft → ready + squash-merged via MCP). Phase 2 found 0 open loop-candidate issues → Phase 3: filed 3 new issues (#99 req-weak-directive, #100 plan-missing-security, #101 spec-pronoun-antecedent). Phase 4 picked #99 (REQ-WEAK-DIRECTIVE — requirement lines using non-normative modals should/may/could/might instead of shall/must); added pitfall + _weak_directive() helper + _WEAK_MODAL_RE/_MANDATORY_MODAL_RE/_STRICT_REQ_ID_LINE_RE constants; _strict_req_mask() scopes strictly to section+FR/NFR labels (avoids false positives on prose); corpus: 2 genuine true positives labelled as accepted_extras; 14 unit tests; pytest 431 green; benchmark good=100 bad=61 precision=0.966 PASS; PR #102 opened (draft); issue #99 commented.
- iter 28 (2026-07-21): Phase 1 merged PR #102 (issue #99 closed, CI was green; converted draft → ready + squash-merged via MCP). Phase 2 found 2 open loop-candidate issues (#100, #101); Phase 4 picked #100 (PLAN-MISSING-SECURITY — deployment plans with no security-hardening vocabulary); added pitfall + _plan_missing_security() helper + _SECURITY_RE constant; reuses _DEPLOY_VOCAB_RE/_DEPLOY_SECTION_RE guard; fires on auth/TLS/encrypt/secret/credential/RBAC/IAM/firewall/vault absence; 17 unit tests; pytest 448 green; benchmark good=100 bad=59.2 PASS; PR #103 opened (draft); issue #100 commented.
- iter 29 (2026-07-22): Phase 1 merged PR #103 (issue #100 closed, CI was green; converted draft → ready + squash-merged via MCP). Phase 2 found 1 open loop-candidate issue (#101); Phase 4 picked #101 (SPEC-PRONOUN-ANTECEDENT — requirement lines with ambiguous object pronoun after modal verb); added pitfall + _pronoun_antecedent() helper + _PRONOUN_ANTECEDENT_RE; _VAGUE_SUBJECT_RE guard prevents double-reporting with SPEC-UNCLEAR-ACTOR; possessive 'its' excluded to avoid false positives; corpus: ambiguous expect_pitfalls + judge.golden merged_overall updated, paraphrased-defects accepted_extras; 15 unit tests; pytest 463 green; benchmark good=100 bad=58.6 precision=0.968 PASS; PR #104 opened (draft); issue #101 commented.
