# Changelog

Notable changes per release. For full per-PR detail, see the
[GitHub releases](https://github.com/hansraj316/sdd-grader/releases).

## [0.4.0]

### Added
- `sddgrade review --jev`: a judge backend built on TypeSafe's Jev. It makes typed
  yes/no judgments for each requirement (ambiguous, unverifiable, compound,
  implementation leak), flags prompt injection in every artifact, and checks
  plan.md against spec.md for over-engineering. Every finding carries Jev's
  probability and a line number. Needs `TYPESAFE_API_KEY`; see
  [docs/jev-judge.md](docs/jev-judge.md).
- 18 new deterministic lint checks:
  - **spec:** `SPEC-FR-COMPOUND`, `SPEC-NFR-AVAILABILITY-UNMEASURED`,
    `SPEC-GHERKIN-BACKGROUND-MISUSED`, `SPEC-GHERKIN-NO-ERROR-SCENARIO`,
    `SPEC-MISSING-INTERFACE-SECTION`, `SPEC-QVSCRIBE-INDIRECT-REFERENCE`
  - **plan:** `PLAN-MISSING-DISTRIBUTED-TRACING`, `PLAN-MISSING-CORS-POLICY`,
    `PLAN-NO-PAGINATION`, `PLAN-MISSING-AUDIT-LOG`, `PLAN-DB-NO-CONNECTION-POOLING`,
    `PLAN-NO-INPUT-VALIDATION`, `PLAN-CONTAINER-NO-RESOURCE-LIMITS`
  - **data model:** `DATA-MODEL-MISSING-SOFT-DELETE`, `DATA-MODEL-NO-CARDINALITY`,
    `DATA-MODEL-ENTITY-NO-INDEX`, `DATA-MODEL-ENTITY-NO-TIMESTAMPS`
- Open-source project files: LICENSE, CONTRIBUTING, CODE_OF_CONDUCT, SECURITY,
  and issue/PR templates.

## [0.3.0]

See the [v0.3.0 release](https://github.com/hansraj316/sdd-grader/releases/tag/v0.3.0).
