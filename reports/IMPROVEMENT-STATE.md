# SDD-Grader Improvement Loop — State

STATUS: ACTIVE
Iteration: 45
Last run: 2026-08-07
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
- [x] xref-dangling-req-ref — XREF-DANGLING-REQ-REF: task references undefined requirement ID → issue #111 → PR #114 → merged 2026-07-26
- [ ] adapter-openspec — Add an OpenSpec adapter (change proposals + specs) behind the existing ArtifactAdapter seam; `--tool openspec` / auto-detect. (OpenSpec)
- [x] report-sarif — already implemented as sddgrade/report/sarif.py (closed issue #14)
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
- [~] spec-qvscribe-and-or — SPEC-QVSCRIBE-AND-OR: 'and/or' ambiguous conjunction on requirement lines (QVscribe Level-1 Clarity / ISO 29148 §5.2.5(a)) → issue #135 → PR #140
- [ ] spec-maqa-ac-conditional — SPEC-MAQA-AC-CONDITIONAL: conditional language (if/unless/may/should) in Gherkin Then clause makes AC non-binary (MAQA binary-verifiability) → issue #136
- [ ] spec-maqa-missing-priority — SPEC-MAQA-MISSING-PRIORITY: spec with 3+ FR- lines but no priority annotation (MoSCoW/P1-P3/High-Low) → issue #137
- [ ] spec-missing-glossary — SPEC-MISSING-GLOSSARY: spec with ≥3 FR-/NFR- lines but no Glossary/Definitions section (ISO 29148 §5.2.1) → issue #138
- [ ] plan-missing-migration — PLAN-MISSING-MIGRATION: plan mentions schema changes (ALTER TABLE/new column) but no data migration strategy (Kiro prod-readiness) → issue #139
- [ ] spec-ears-trigger-inversion — SPEC-EARS-TRIGGER-INVERSION: 'shall' before EARS trigger keyword (inverted ordering) — from EARS research
- [ ] spec-qvscribe-temporal-unbounded — SPEC-QVSCRIBE-TEMPORAL-UNBOUNDED: 'always'/'never'/'at all times' temporal universals (QVscribe Continuance) — from research
- [ ] spec-qvscribe-weakened-except — SPEC-QVSCRIBE-WEAKENED-EXCEPT: shall/must qualified with 'except'/'unless' open-ended carve-out (QVscribe Weakness) — from research
- [ ] spec-missing-motivation — SPEC-MISSING-MOTIVATION: spec with requirements but no Problem Statement/Motivation section (Kiro spec template) — from research
- [ ] plan-hardcoded-config — PLAN-HARDCODED-CONFIG: IPv4:port or credential patterns on non-fenced plan lines (Tessl/Twelve-Factor) — from research
- [ ] spec-nfr-no-unit — SPEC-NFR-NO-UNIT: NFR with numeric threshold but no measurement unit (Canon Scale/Meter/Must) — from research
- [x] spec-req-section-prose-only — SPEC-REQ-SECTION-PROSE-ONLY: requirements section with prose but no normative statements (IBM RQA, QVscribe, ISO 29148) → issue #112 → PR #115 → merged 2026-07-27
- [x] plan-third-party-no-fallback — PLAN-THIRD-PARTY-NO-FALLBACK: plan mentions external service/API but no resilience vocabulary (Kiro, Tessl, ISO 25010) → issue #113 → merged in PR #116
- [x] plan-missing-health-check — PLAN-MISSING-HEALTH-CHECK: deployment plan with no health-check/liveness/readiness-probe mention (Kiro production-readiness, ISO 25010 Availability) → issue #117 → PR #120 → merged 2026-07-29
- [x] xref-ac-no-task — XREF-AC-NO-TASK: AC-NNN defined in spec.md but never referenced by any task in tasks.md (ISO 29148 §5.2.6 bidirectional traceability) → issue #118 → PR #121 → merged 2026-07-31
- [x] spec-req-no-id — SPEC-REQ-NO-ID: normative requirement line (shall/must) in Requirements section with no FR-/NFR-/AC-/US- identifier (QVscribe Identifiability, IBM RQA, ISO 29148 §5.2.6) → issue #119 → PR #122 → merged 2026-07-31
- [x] tasks-no-estimate — TASKS-NO-ESTIMATE: task file with T## IDs but no effort estimate annotation (story points, t-shirt size, hours) — INVEST Estimable criterion → issue #123 → PR #126 → merged 2026-08-01
- [x] spec-ac-no-fr-link — SPEC-AC-NO-FR-LINK: spec uses both FR-NNN and AC-NNN identifiers but no line co-references both — Canon Fit Criterion / MAQA Traceability → issue #131 → PR #134 → merged 2026-08-06
- [x] spec-story-compound — SPEC-STORY-COMPOUND: user story header with 2+ wants joined by "and" (INVEST Small violation) → issue #124 → PR #128 → merged 2026-08-04
- [x] spec-missing-out-of-scope — SPEC-MISSING-OUT-OF-SCOPE: spec with substantial reqs but no out-of-scope/non-goal heading (Kiro, Tessl, ISO 29148) → issue #125 → PR #127 → merged 2026-08-02
- [x] spec-ac-vague-outcome — SPEC-AC-VAGUE-OUTCOME: Gherkin Then clause with vague outcome words (correctly/properly/as expected) with no observable condition (MAQA binary-verifiable AC rule) → issue #130 → PR #132 → merged 2026-08-05
- [~] spec-fr-no-story — SPEC-FR-NO-STORY: FR-/NFR- line in spec outside any US-NNN section and no [US#] tag (Canon/29148 traceability) → issue #129 → PR #133
- [x] tasks-untraced-task — TASKS-UNTRACED-TASK pitfall: checkbox task with T## id but no [US#] tag and no FR-/NFR-/AC-/US- reference (ISO 29148 bidirectional traceability, Kiro/MAQA/Canon) → issue #105 → PR #108 → merged 2026-07-24
- [x] spec-future-tense-req — SPEC-FUTURE-TENSE-REQ pitfall: requirement lines using "will be"/"would be" instead of normative "shall"/"must" (ISO 29148, Canon) → issue #106 → PR #109 → merged 2026-07-25
- [x] plan-missing-capacity — PLAN-MISSING-CAPACITY pitfall: deployment plan with scaling vocab but no capacity numbers (Tessl, ISO 25010 Capacity) → issue #107 → PR #110 → merged 2026-07-25
- [x] story-no-benefit — SPEC-STORY-NO-BENEFIT pitfall: "As a X, I want Y" without "so that Z" clause. (INVEST Valuable, Connextra, ISO 29148) → issue #87 → PR #90 → merged 2026-07-15
- [x] unbounded-scope — REQ-UNBOUNDED-SCOPE pitfall: "etc.", "and so on" in requirements. (ISO 29148, QVscribe) → issue #88 → PR #91 → merged 2026-07-16
- [x] plan-missing-rollback — PLAN-MISSING-ROLLBACK pitfall: plan.md with no rollback/revert/fallback mention. (Spec-Kit, ISO 25010) → issue #89 → PR #92 → merged 2026-07-17
- [x] req-duplicate-id — REQ-DUPLICATE-ID pitfall: same FR/NFR/AC/US identifier on multiple lines. (ISO 29148, QVscribe) → issue #93 → PR #96 → merged 2026-07-18
- [x] plan-no-testing-strategy — PLAN-NO-TESTING-STRATEGY pitfall + _plan_no_testing_strategy() helper; _PHASE_HEADING_RE + _TESTING_VOCAB_RE constants; 2-phase guard prevents false positives on short plans; 13 unit tests; pytest 403 green; benchmark good=100 bad=61 PASS → issue #94 → PR #97 → merged 2026-07-19
- [x] plan-missing-observability — PLAN-MISSING-OBSERVABILITY pitfall + _plan_missing_observability() helper; _OBSERVABILITY_RE constant; reuses _DEPLOY_VOCAB_RE/_DEPLOY_SECTION_RE guard; fires on monitoring/logging/metrics/alerting/SLO/SLA absence; 14 unit tests; pytest 417 green; benchmark good=100 bad=61 PASS → issue #95 → PR #98 → merged 2026-07-20
- [x] req-weak-directive — REQ-WEAK-DIRECTIVE pitfall + _weak_directive() helper; _WEAK_MODAL_RE/_MANDATORY_MODAL_RE/_STRICT_REQ_ID_LINE_RE constants; _strict_req_mask() scopes to section+label only (avoids false positives on prose "should"); 14 unit tests; pytest 431 green; benchmark good=100 bad=61 precision=0.966 PASS → issue #99 → PR #102 → merged 2026-07-21
- [x] plan-missing-security — PLAN-MISSING-SECURITY pitfall + _plan_missing_security() helper; _SECURITY_RE constant; reuses _DEPLOY_VOCAB_RE/_DEPLOY_SECTION_RE guard; fires on auth/TLS/encrypt/secrets/RBAC/IAM/firewall/vault absence; 17 unit tests; pytest 448 green; benchmark good=100 bad=59.2 PASS → issue #100 → PR #103 → merged 2026-07-22
- [x] spec-pronoun-antecedent — SPEC-PRONOUN-ANTECEDENT; object pronouns (it/them/their/this/that/these/those) after modal verb; _VAGUE_SUBJECT_RE guard avoids double-count with SPEC-UNCLEAR-ACTOR; possessive 'its' excluded; 15 unit tests; pytest 463 green; benchmark good=100 bad=58.6 precision=0.968 PASS → issue #101 → PR #104 → merged 2026-07-22

(The loop's research phase expands this list from OpenSpec, AIDE, Canon, MAQA, Kiro,
Tessl, and Spec-Kit extensions/presets.)

## In PR

- #135 → PR #140 spec-qvscribe-and-or — SPEC-QVSCRIBE-AND-OR: 'and/or' ambiguous conjunction on requirement-bearing lines; _AND_OR_RE constant + _spec_qvscribe_and_or() helper; scoped via _requirement_mask() + _fence_mask(); 11 unit tests (5 fire, 6 silent); pytest 702 green; benchmark good=100 bad=56.8 precision=0.971 PASS; awaiting CI.

## Merged

- #131 → PR #134 spec-ac-no-fr-link — SPEC-AC-NO-FR-LINK: spec defines both FR-NNN and AC-NNN identifiers but no line co-references both; _FR_ID_RE + _AC_NNN_RE constants; guard: both types must appear; 10 unit tests (3 fire, 7 silent); pytest 691 green; benchmark good=100 bad=56.8 precision=0.971 PASS (2026-08-06, CI was green; squash-merged).
- #129 → PR #133 spec-fr-no-story — SPEC-FR-NO-STORY: FR-/NFR- line outside any US-NNN section with no [US#] link; _US_NNN_TITLE_RE guard; section-boundary scan via art.sections; fenced-block exclusion; 13 unit tests (5 fire, 8 silent); pytest 681 green; benchmark good=100 bad=56.8 precision=0.971 PASS (2026-08-06, CI was green; squash-merged).
- #130 → PR #132 spec-ac-vague-outcome — SPEC-AC-VAGUE-OUTCOME: vague outcome adverb (correctly/properly/appropriately/as expected/as intended) in Gherkin Then clause; formal-Gherkin guard (Given+When line-leaders required); _VAGUE_OUTCOME_RE constant; 14 unit tests (6 fire, 8 silent); pytest 668 green; benchmark good=100 bad=56.8 precision=0.971 PASS (2026-08-05, CI was green; squash-merged).
- #124 → PR #128 spec-story-compound — SPEC-STORY-COMPOUND: compound user-story header (INVEST Small); _I_WANT_TO_RE guard avoids adj-want false positives; 15 unit tests; pytest 654 green; benchmark good=100 bad=56.8 precision=0.971 PASS (2026-08-04, CI was green; squash-merged).
- #125 → PR #127 spec-missing-out-of-scope — SPEC-MISSING-OUT-OF-SCOPE pitfall + _spec_missing_out_of_scope() helper; _OUT_OF_SCOPE_HEADING_RE + _NORMATIVE_LINE_RE constants; ≥3-normative-line guard; 15 unit tests; pytest 639 green; benchmark good=100 bad=56.8 precision=0.971 PASS (2026-08-02, CI was green; squash-merged).
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
- #101 → PR #104 spec-pronoun-antecedent — SPEC-PRONOUN-ANTECEDENT pitfall + _pronoun_antecedent() helper; _PRONOUN_ANTECEDENT_RE; 15 unit tests; pytest 463 green; benchmark good=100 bad=58.6 precision=0.968 PASS (2026-07-22, CI was green; squash-merged).
- #105 → PR #108 tasks-untraced-task — TASKS-UNTRACED-TASK pitfall + _tasks_untraced_task() helper; fenced-block exclusion; applies only to tasks artifacts; fixture T001/T002 updated with [US1] tag; 15 unit tests; pytest 478 green; benchmark good=100 bad=58.6 PASS (2026-07-24, CI was green; squash-merged).
- #106 → PR #109 spec-future-tense-req — SPEC-FUTURE-TENSE-REQ pitfall + _future_tense_req() helper; _FUTURE_TENSE_RE constant; reuses _strict_req_mask()/_MANDATORY_MODAL_RE; skips mixed normative statements (shall/must on same line); 19 unit tests; pytest 497 green; benchmark good=100 bad=58.6 precision=0.968 PASS (2026-07-25, CI was green; squash-merged).
- #111 → PR #114 xref-dangling-req-ref — XREF-DANGLING-REQ-REF cross-artifact pitfall + _US_TAG_NUM_RE; _cross_artifact() check; fenced-block exclusion; 15 unit tests; pytest 531 green; benchmark good=100 bad=58.6 PASS (2026-07-26, CI was green; squash-merged).
- #112 → PR #115 spec-req-section-prose-only — SPEC-REQ-SECTION-PROSE-ONLY pitfall + _PROSE_REQ_SECTION_RE + _FORMAL_REQ_INDICATOR_RE constants + _req_section_prose_only() helper; fenced-block exclusion; 16 unit tests; pytest 547 green; benchmark good=100 bad=58.6 precision=0.968 PASS (2026-07-27, CI was green; squash-merged).
- #113 → PR #116 plan-third-party-no-fallback — PLAN-THIRD-PARTY-NO-FALLBACK pitfall + _THIRD_PARTY_RE + _RESILIENCE_RE constants + _plan_third_party_no_fallback() helper; wired into _plan_checks(); 17 unit tests (8 fire, 9 silent); pytest 564 green; benchmark good=100 bad=58.6 precision=0.968 PASS (2026-07-28, CI was green; squash-merged).
- #107 → PR #110 plan-missing-capacity — PLAN-MISSING-CAPACITY pitfall + _plan_missing_capacity() helper; _SCALING_VOCAB_RE + _CAPACITY_NUMBER_RE constants; fires when scaling vocab present but no capacity numbers; 19 unit tests; pytest 516 green; benchmark good=100 bad=58.6 precision=0.968 PASS (2026-07-25, CI was green; squash-merged same run).
- #117 → PR #120 plan-missing-health-check — PLAN-MISSING-HEALTH-CHECK pitfall + _HEALTH_CHECK_RE constant + _plan_missing_health_check() helper; reuses _DEPLOY_VOCAB_RE/_DEPLOY_SECTION_RE guard; 14 unit tests (6 fire, 8 silent); pytest 578 green; benchmark good=100 bad=58.6 precision=0.968 PASS (2026-07-29, CI was green; squash-merged).
- #118 → PR #121 xref-ac-no-task — XREF-AC-NO-TASK pitfall + _AC_ID_RE constant + cross-artifact check in _cross_artifact(); fenced-block/heading exclusion; restricts task-side scan to checkbox lines; 13 unit tests; pytest 591 green; benchmark good=100 bad=58.6 PASS (2026-07-31, CI was green; squash-merged).
- #119 → PR #122 spec-req-no-id — SPEC-REQ-NO-ID pitfall + _req_no_id() helper; scoped to _REQ_SECTION_TITLE_RE sections; guard skips pure-prose sections; reuses _MANDATORY_MODAL_RE/_STRICT_REQ_ID_LINE_RE/_fence_mask(); aggregate finding anchored to first offending line; 17 unit tests; pytest 608 green; benchmark good=100 bad=58.6 precision=0.968 PASS (2026-07-31, CI was green; squash-merged same run).
- #123 → PR #126 tasks-no-estimate — TASKS-NO-ESTIMATE pitfall + _tasks_no_estimate() helper; _ESTIMATE_RE constant; ≥3-task threshold; fenced-block exclusion; good fixture + feature-xref corpus updated; 16 unit tests; pytest 624 green; benchmark good=100 bad=58.6 precision=0.969 PASS (2026-08-01, CI was green; squash-merged).

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
- iter 30 (2026-07-23): Phase 1 no open loop/* PRs (PR #104 already merged same run as iter 29). Phase 2 found 0 open loop-candidate issues → Phase 3: filed 3 new issues (#105 tasks-untraced-task, #106 spec-future-tense-req, #107 plan-missing-capacity; research via Kiro/MAQA/Canon/Tessl parallel agents). Phase 4 picked #105 (TASKS-UNTRACED-TASK — checkbox task with T## id but no [US#] tag and no FR-/NFR-/AC-/US- reference; reverse of XREF-STORY-NO-TASK; ISO 29148 bidirectional traceability); added pitfall + _tasks_untraced_task() helper; fenced-block exclusion; fixture T001/T002 updated with [US1] tag in good corpus; 15 unit tests; pytest 478 green; benchmark good=100 bad=58.6 PASS; PR #108 opened (draft); issue #105 commented.
- iter 31 (2026-07-24): Phase 1 merged PR #108 (issue #105 closed, CI was green; converted draft → ready + squash-merged via MCP). Phase 2 found 2 open loop-candidate issues (#106, #107); Phase 4 picked #106 (SPEC-FUTURE-TENSE-REQ — requirement lines using future-tense "will be"/"would be" instead of normative "shall"/"must"; enforceability defect distinct from REQ-WEAK-DIRECTIVE's optionality defect; ISO 29148 §5.2.5, Canon, MAQA); added pitfall + _future_tense_req() helper + _FUTURE_TENSE_RE constant; reuses _strict_req_mask()/_MANDATORY_MODAL_RE; skips mixed normative statements; 19 unit tests; pytest 497 green; benchmark good=100 bad=58.6 precision=0.968 PASS; PR #109 opened (draft); issue #106 commented.
- iter 32 (2026-07-25): Phase 1 merged PR #109 (issue #106 closed, CI was green; converted draft → ready + squash-merged via MCP). Phase 2 found 1 open loop-candidate issue (#107); Phase 4 picked #107 (PLAN-MISSING-CAPACITY — deployment plans that mention scaling vocab but state no concrete capacity numbers; Tessl spec-first + ISO/IEC 25010 Capacity §4.2.1.2); added pitfall + _plan_missing_capacity() helper + _SCALING_VOCAB_RE + _CAPACITY_NUMBER_RE constants; guard: fires only when scaling vocab present; silent when any capacity number (digit + resource unit) found; 19 unit tests; pytest 516 green; benchmark good=100 bad=58.6 precision=0.968 PASS; PR #110 opened (draft); CI turned green same run; PR #110 converted + squash-merged; issue #107 closed.
- iter 33 (2026-07-26): Phase 1 no open loop/* PRs. Phase 2 found 0 open loop-candidate issues → Phase 3: fanned 3 parallel research agents (SARIF/traceability, INVEST/Kiro/MAQA/Canon, Tessl/OpenSpec/Spec-Kit); filed 3 new issues (#111 XREF-DANGLING-REQ-REF, #112 SPEC-REQ-SECTION-PROSE-ONLY, #113 PLAN-THIRD-PARTY-NO-FALLBACK). Phase 4 picked #111 (XREF-DANGLING-REQ-REF — task line references a [US#]/FR-/NFR-/AC-/US- ID not defined in spec.md; ISO 29148 bidirectional traceability); added pitfall + _US_TAG_NUM_RE constant + cross-artifact check in _cross_artifact(); fenced-block exclusion; guard when spec defines no formal IDs; 15 unit tests; pytest 531 green; benchmark good=100 bad=58.6 PASS; PR #114 opened (draft); CI turned green same run; PR #114 converted + squash-merged; issue #111 closed.
- iter 34 (2026-07-27): Phase 1 no open loop/* PRs. Phase 2 found 2 open loop-candidate issues (#112, #113); Phase 4 picked #112 (SPEC-REQ-SECTION-PROSE-ONLY — requirements section with substantial prose but no shall/must modals or FR-/NFR-/AC-/US- IDs; IBM RQA L1 Completeness / QVscribe Identifiability / ISO 29148 §5.2); added pitfall + _PROSE_REQ_SECTION_RE + _FORMAL_REQ_INDICATOR_RE constants + _req_section_prose_only() helper wired into _spec_checks(); fenced-block exclusion prevents code samples suppressing findings; 16 unit tests; pytest 547 green; benchmark good=100 bad=58.6 precision=0.968 PASS; PR #115 opened (draft); CI green same run; PR #115 converted + squash-merged; issue #112 closed.
- iter 35 (2026-07-28): Phase 1 no open loop/* PRs. Phase 2 found 1 open loop-candidate issue (#113); Phase 4 picked #113 (PLAN-THIRD-PARTY-NO-FALLBACK — plan names external API/service/webhook/OAuth but has no resilience vocabulary; Amazon Kiro production-readiness, Tessl spec-first, ISO 25010 Fault Tolerance §4.2.1.4); added pitfall + _THIRD_PARTY_RE + _RESILIENCE_RE constants + _plan_third_party_no_fallback() helper wired into _plan_checks(); 17 unit tests (8 fire, 9 silent); pytest 564 green; benchmark good=100 bad=58.6 precision=0.968 PASS; PR #116 opened; CI green same run; converted + squash-merged; issue #113 closed.
- iter 36 (2026-07-29): Phase 1 no open loop/* PRs. Phase 2 found 0 open loop-candidate issues → Phase 3: fanned 3 parallel research agents (INVEST/MAQA/Canon, Kiro/Tessl/ISO-25010, ISO-29148/IBM-RQA); filed 3 new issues (#117 PLAN-MISSING-HEALTH-CHECK, #118 XREF-AC-NO-TASK, #119 SPEC-REQ-NO-ID); also surfaced 2 additional ideas for pool (TASKS-NO-ESTIMATE, SPEC-AC-NO-FR-LINK). Phase 4 picked #117 (PLAN-MISSING-HEALTH-CHECK — deployment plan with no health-check/probe; Amazon Kiro production-readiness, ISO 25010 Availability §4.2.1.3; distinct from PLAN-MISSING-OBSERVABILITY); added pitfall + _HEALTH_CHECK_RE constant + _plan_missing_health_check() helper reusing _DEPLOY_VOCAB_RE/_DEPLOY_SECTION_RE guard; wired into _plan_checks(); 14 unit tests (6 fire, 8 silent); pytest 578 green; benchmark good=100 bad=58.6 precision=0.968 PASS; PR #120 opened; CI green same run; converted + squash-merged; issue #117 closed.
- iter 37 (2026-07-30): Phase 1 no open loop/* PRs. Phase 2 found 2 open loop-candidate issues (#118, #119); Phase 4 picked #118 (XREF-AC-NO-TASK — AC-NNN defined in spec.md but never cited by any checkbox task line in tasks.md; ISO 29148 §5.2.6 forward traceability from AC to implementing task; fills the last gap in the 4-direction traceability matrix); added pitfall + _AC_ID_RE module-level constant + XREF-AC-NO-TASK block in _cross_artifact(); fenced-block/heading exclusion on spec side; checkbox-line filter on task side; one aggregate finding anchored to spec.md; 13 unit tests; pytest 591 green; benchmark good=100 bad=58.6 PASS; PR #121 opened (draft); awaiting CI.
- iter 38 (2026-07-31): Phase 1 merged PR #121 (issue #118 closed, CI was green; converted draft → ready + squash-merged via MCP). Phase 2 found 1 open loop-candidate issue (#119); Phase 4 picked #119 (SPEC-REQ-NO-ID — normative requirement line with shall/must in a Requirements/Acceptance/Scenario section but no FR-/NFR-/AC-/US-NNN identifier; QVscribe Level-1 Identifiability, IBM RQA labeling prerequisite, ISO 29148 §5.2.6; distinct from SPEC-REQ-SECTION-PROSE-ONLY and REQ-DUPLICATE-ID); added pitfall + _req_no_id() helper; guard skips pure-prose sections; reuses _REQ_SECTION_TITLE_RE/_MANDATORY_MODAL_RE/_STRICT_REQ_ID_LINE_RE/_fence_mask(); 17 unit tests; pytest 608 green; benchmark good=100 bad=58.6 precision=0.968 PASS; PR #122 opened; CI green same run; converted + squash-merged; issue #119 closed.
- iter 39 (2026-08-01): Phase 1 no open loop/* PRs. Phase 2 found 0 open loop-candidate issues → Phase 3: fanned 2 parallel research agents (Kiro/Tessl/OpenSpec → SPEC-MISSING-OUT-OF-SCOPE, SPEC-MISSING-ASSUMPTIONS, SPEC-NO-PRIORITY-LABELS; INVEST/MAQA/Canon → SPEC-AC-VAGUE-OUTCOME, SPEC-STORY-COMPOUND, SPEC-FR-NO-STORY); filed 3 new issues (#123 tasks-no-estimate, #124 spec-story-compound, #125 spec-missing-out-of-scope); also added 2 ideas to pool (spec-ac-vague-outcome, spec-fr-no-story). Phase 4 picked #123 (TASKS-NO-ESTIMATE — tasks.md with 3+ T## checkbox tasks but no effort estimate annotation; INVEST Estimable criterion); added pitfall + _ESTIMATE_RE constant + _tasks_no_estimate() helper wired into _tasks_checks(); good fixture tasks.md updated with (1 sp); feature-xref corpus case accepted_extras + golden score updated 90.4→89.9; 16 unit tests; pytest 624 green; benchmark good=100 bad=58.6 precision=0.969 PASS; PR #126 opened; CI green same run; converted + squash-merged; issue #123 closed.
- iter 40 (2026-08-02): Phase 1 no open loop/* PRs. Phase 2 found 2 open loop-candidate issues (#124, #125). Phase 4 picked #125 (SPEC-MISSING-OUT-OF-SCOPE — spec with ≥3 normative requirement lines but no Out-of-Scope/Non-Goals heading; Amazon Kiro, Tessl, ISO 29148 §5.2.4); added pitfall + _OUT_OF_SCOPE_HEADING_RE + _NORMATIVE_LINE_RE constants + _spec_missing_out_of_scope() helper wired into _spec_checks(); good fixture spec.md updated with ## Out of Scope section; corpus accepted_extras labeled for paraphrased-defects + realworld-mcp-proxy; 15 unit tests; pytest 639 green; benchmark good=100 bad=56.8 precision=0.971 PASS; PR #127 opened (draft); awaiting CI.
- iter 41 (2026-08-03): Phase 1 no open loop/* PRs (0). Phase 2 found 1 open loop-candidate issue (#124); Phase 4 picked #124 (SPEC-STORY-COMPOUND — Connextra story opener with "I want to X and Y" bundles ≥2 capabilities; INVEST Small, MAQA Level-2 compound AC); added pitfall + _I_WANT_TO_RE + _COMPOUND_AND_RE constants + _spec_story_compound() helper wired into _spec_checks(); "to" guard avoids adjective-want false positive ("I want fast and intuitive search"); 15 unit tests; pytest 654 green; benchmark good=100 bad=56.8 precision=0.971 PASS; PR #128 opened (draft); awaiting CI.
- iter 42 (2026-08-04): Phase 1 merged PR #128 (issue #124 closed, CI was green; converted draft → ready + squash-merged via MCP). Phase 2 found 0 open loop-candidate issues → Phase 3: promoted 3 pool items to issues (#129 SPEC-FR-NO-STORY, #130 SPEC-AC-VAGUE-OUTCOME, #131 SPEC-AC-NO-FR-LINK). Phase 4 picked #130 (SPEC-AC-VAGUE-OUTCOME — Then clause in formal-Gherkin AC with vague non-observable adverb; MAQA binary-verifiable AC rule; formal-Gherkin guard requires both Given+When line-leaders to suppress false positives on prose ACs); added pitfall + _VAGUE_OUTCOME_RE constant + _spec_ac_vague_outcome() helper wired into _spec_checks(); 14 unit tests (6 fire, 8 silent); pytest 668 green; benchmark good=100 bad=56.8 precision=0.971 PASS; PR #132 opened (draft); awaiting CI.
- iter 43 (2026-08-05): Phase 1 merged PR #132 (issue #130 closed, CI was green; converted draft → ready + squash-merged via MCP). Phase 2 found 2 open loop-candidate issues (#129, #131). Phase 4 picked #129 (SPEC-FR-NO-STORY — FR-/NFR- line in spec outside any US-NNN section with no [US#] link; Canon Fit Criterion traceability, ISO 29148 §5.2.6; fills FR→US direction of bidirectional traceability matrix); added pitfall + _US_NNN_TITLE_RE + _FR_NFR_LINE_RE constants + _spec_fr_no_story() helper wired into _spec_checks(); _US_NNN_TITLE_RE guard fires only for specs with literal US-NNN headings (avoids false positives on standard "User Story N" format); section-boundary scan via art.sections; fenced-block exclusion; 13 unit tests (5 fire, 8 silent); pytest 681 green; benchmark good=100 bad=56.8 precision=0.971 PASS; PR #133 opened (draft); awaiting CI.
- iter 44 (2026-08-06): Phase 1 merged PR #133 (issue #129 closed, CI was green; converted draft → ready + squash-merged via MCP). Phase 2 found 1 open loop-candidate issue (#131). Phase 4 picked #131 (SPEC-AC-NO-FR-LINK — spec defines both FR-NNN and AC-NNN identifiers but no single non-fenced line co-references both; Canon Fit Criterion / MAQA Traceability Level-2); added pitfall + _FR_ID_RE + _AC_NNN_RE constants + _spec_ac_no_fr_link() helper wired into _spec_checks(); guard fires only when both FR-NNN and AC-NNN identifiers appear; NFR-NNN correctly excluded (\bFR-\d+\b won't match NFR at a word boundary); fenced-block co-references excluded; 10 unit tests (3 fire, 7 silent); pytest 691 green; benchmark good=100 bad=56.8 precision=0.971 PASS; PR #134 opened; CI green same run; converted + squash-merged; issue #131 closed.
- iter 45 (2026-08-07): Phase 1 no open loop/* PRs. Phase 2 found 0 open loop-candidate issues → Phase 3: fanned 2 parallel research agents (EARS/QVscribe/MAQA → 9 ideas; ISO 29148/Kiro/Tessl/Canon → 9 ideas); filed 5 new issues (#135 SPEC-QVSCRIBE-AND-OR, #136 SPEC-MAQA-AC-CONDITIONAL, #137 SPEC-MAQA-MISSING-PRIORITY, #138 SPEC-MISSING-GLOSSARY, #139 PLAN-MISSING-MIGRATION); also surfaced 6 additional ideas for pool (SPEC-EARS-TRIGGER-INVERSION, SPEC-QVSCRIBE-TEMPORAL-UNBOUNDED, SPEC-QVSCRIBE-WEAKENED-EXCEPT, SPEC-MISSING-MOTIVATION, PLAN-HARDCODED-CONFIG, SPEC-NFR-NO-UNIT). Phase 4 picked #135 (SPEC-QVSCRIBE-AND-OR — 'and/or' ambiguous conjunction on requirement-bearing lines; QVscribe Level-1 Clarity defect, ISO 29148 §5.2.5(a) 'unambiguous'; scoped via _requirement_mask()/_fence_mask(); 11 unit tests (5 fire, 6 silent)); pytest 702 green; benchmark good=100 bad=56.8 precision=0.971 PASS; PR #140 opened (draft); awaiting CI.
