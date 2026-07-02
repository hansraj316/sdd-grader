# SDD Artifact Pitfalls — Research-Backed Catalog

This document grounds `rubric/pitfalls.toml`. It catalogs the concrete quality defects
a reviewer can detect in Spec-Driven Development artifacts (GitHub Spec-Kit `spec.md`,
`plan.md`, `tasks.md`, constitution), why each hurts, how to detect it, and how to fix
it. Each pitfall in the TOML carries a stable `id` so findings and history stay
reproducible across runs and releases.

## Sources

- **Spec-Kit methodology & templates** — `github/spec-kit`: the SDD methodology doc and
  the `spec-template.md` / `plan-template.md` / `tasks-template.md` /
  `constitution-template.md` define the intended structure, the `[NEEDS CLARIFICATION]`
  marker, the Constitution Check gate, Complexity Tracking, measurable Success Criteria,
  INDEPENDENTLY-TESTABLE user stories, and the WHAT-not-HOW spec discipline.
  <https://github.com/github/spec-kit/blob/main/spec-driven.md>
- **ISO/IEC/IEEE 29148:2018** — requirements quality characteristics: *necessary,
  appropriate, unambiguous, complete, singular, feasible, verifiable, correct,
  conforming*, plus traceability. <https://www.iso.org/standard/72089.html>
- **Requirements Smells** (Femmer et al.) — a practical, mostly lexical approach to
  detecting requirements-quality defects (subjective/vague terms, comparatives without a
  reference, loopholes, non-verifiable terms). <https://arxiv.org/pdf/1611.08847>
- **INVEST** for user stories — Independent, Negotiable, Valuable, Estimable, Small,
  Testable. <https://agilealliance.org/glossary/invest/>
- **Acceptance criteria / BDD (Gherkin)** — testable conditions of satisfaction,
  Given/When/Then. <https://cucumber.io/docs/gherkin/>
- **Real-world Spec-Kit critiques** — specs as "pseudo-documentation"/noise that
  stakeholders can't consume; natural-language specs can't self-verify; over-engineering.
  <https://dev.to/kotaroyamame/github-spec-kit-is-80-right-heres-the-missing-20-that-would-make-it-transformative-2bi6>,
  <https://github.com/github/spec-kit/discussions/152>

## How detection is split

- **`lint`** — deterministic, free, reproducible. Markers, placeholders, lexical smells,
  section presence, format, and cross-artifact traceability links.
- **`judge`** — semantic judgment the lint layer can't do (true ambiguity, hidden
  contradictions, over-engineering, INVEST quality). Runs in the user's agent.
- **`both`** — lint catches the obvious cases cheaply; the judge catches the rest.

## Catalog (summary)

| id | artifact | dimension | detect |
|----|----------|-----------|--------|
| SPEC-UNRESOLVED-CLARIFICATION | spec, plan | completeness | lint: count unresolved `[NEEDS CLARIFICATION]` |
| SPEC-LEFTOVER-PLACEHOLDER | all | completeness | lint: template placeholders, TODO/TBD/FIXME, `$ARGUMENTS` |
| SPEC-AMBIGUOUS-WORDING | spec, plan | clarity | lint: vague/subjective terms (Requirements Smells) |
| SPEC-COMPARATIVE-NO-REFERENCE | spec | clarity | lint: comparatives ("faster", "better") with no baseline |
| SPEC-IMPL-DETAIL-LEAK | spec | clarity | lint+judge: tech-stack tokens in the spec |
| SPEC-NON-MEASURABLE-SUCCESS | spec | testability | lint+judge: Success Criteria with no number/unit |
| SPEC-MISSING-ACCEPTANCE | spec | testability | lint+judge: user story without acceptance/Given-When-Then |
| SPEC-NON-INDEPENDENT-STORY | spec | traceability | judge: INVEST independence/small |
| SPEC-SPECULATIVE-FEATURE | spec, plan | feasibility | lint+judge: "might need"/"future"/"nice to have" |
| SPEC-MISSING-EDGE-CASES | spec | completeness | lint: Edge Cases empty/placeholder |
| REQ-COMPOUND | spec | clarity | lint+judge: multi-capability requirement (singular) |
| PLAN-CONSTITUTION-UNCHECKED | plan | constitutional | lint: no/!passed Constitution Check |
| PLAN-UNJUSTIFIED-COMPLEXITY | plan | constitutional | lint+judge: violations w/o Complexity Tracking |
| PLAN-OVER-ENGINEERING | plan | feasibility | judge: speculative abstraction layers |
| PLAN-NO-RATIONALE | plan | traceability | judge: tech choice without documented rationale |
| TASKS-TESTS-NOT-FIRST | tasks | constitutional | lint: implementation before tests within a story |
| TASKS-MALFORMED | tasks | consistency | lint: missing ID/checkbox, malformed `[P]`/`[US]` |
| TASKS-VAGUE | tasks | clarity | lint+judge: no file path / concrete action |
| XREF-STORY-NO-TASK | spec↔tasks | traceability | lint: user story with no implementing task |
| XREF-ENTITY-NO-TASK | data-model↔tasks | traceability | lint: entity with no task |
| XREF-CONTRACT-NO-TEST | contracts↔tasks | traceability | lint: contract with no contract-test task |
| XREF-CONTRADICTION | spec/plan/tasks | consistency | judge: cross-artifact contradiction |
| CONST-PLACEHOLDER | constitution | constitutional | lint: unfilled principle/version placeholders |
| CONST-UNVERSIONED | constitution | constitutional | lint: missing version/ratification metadata |

The authoritative, machine-readable form (with `why`, `detect`, `fix`, severities, and
lint parameters) lives in [`../rubric/pitfalls.toml`](../rubric/pitfalls.toml).

## Notes / open items

- Spec-Kit's actual `constitution-template.md` ships generic placeholder principles, not
  the example Library-First / CLI / Test-First "articles" from the methodology doc. So
  the constitutional checks are about the **Constitution Check gate being addressed and
  violations justified**, plus the project's own principles being filled in — not about
  hardcoding four specific gate names.
- The lexical smell list is intentionally conservative to keep false positives low; the
  judge is responsible for nuanced ambiguity. The list is the seam the future
  self-updating `/loop` will expand as upstream tools and practice evolve.
