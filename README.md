# sddreview

**An external quality gate for [GitHub Spec-Kit](https://github.com/github/spec-kit) artifacts.**

Spec-Kit (and OpenSpec) generate spec-driven-development artifacts — `spec.md`,
`plan.md`, `tasks.md`, a constitution — but nothing tells you whether a given spec
is actually *good*: complete, unambiguous, testable, traceable, and aligned with its
constitution. `sddreview` does. It grades each artifact 0–100 across quality
dimensions, attaches a concrete **fix suggestion** to every finding, flags known
**SDD pitfalls**, tracks score **history**, and gates CI — all from a simple CLI that
installs and behaves like `specify` itself.

## How it works

A **hybrid engine**:

- **Deterministic lint** (free, offline, reproducible) — turns Spec-Kit's own
  conventions into measurable signals: unresolved `[NEEDS CLARIFICATION]` markers,
  constitutional gates (Simplicity / Anti-Abstraction / Integration-First / Test-First),
  the traceability chain (story → scenario → task, entity → task, contract → test),
  `[P]` task hygiene, and WHAT-not-HOW spec discipline.
- **LLM semantic judge** — runs **inside your existing AI agent** (Claude Code,
  Copilot, Cursor, Gemini…) using the subscription you already have, **no API key**.
  `sddreview init --integration <agent>` scaffolds a slash command; your agent judges
  the artifacts and writes structured JSON back, which the CLI merges and scores. A
  key-based `--api` backend exists for headless CI, and `--rules` runs lint-only.

## Install

```bash
uv tool install sddreview --from git+https://github.com/<you>/sddreview.git
# or zero-install:
uvx --from git+https://github.com/<you>/sddreview.git sddreview review
```

## Commands

```bash
sddreview init --integration claude   # scaffold config + agent judge slash command
sddreview review                      # grade every artifact (lint + agent judgment if present)
sddreview review --rules --json       # offline, machine-readable (good for CI)
sddreview review --fail-under 70      # non-zero exit below threshold (CI gate)
sddreview advise                      # recommend how to adopt SDD for this codebase
sddreview dashboard                   # terminal metrics: trends, dimensions, top pitfalls
sddreview self check                  # version
sddreview integration list            # supported agents
```

## Relationship to Spec-Kit

Spec-Kit ships in-agent `/speckit.analyze`, `/speckit.checklist`, and
`/speckit.clarify`. `sddreview` is the **external, scored, reproducible, CI-gating,
history-tracking** complement — it runs outside the agent, emits a numeric benchmark
+ JSON + exit code, and can consume those commands' outputs as extra signals.

## Status

Phase 1 (Spec-Kit only). Roadmap: OpenSpec adapter, tool-vs-tool benchmark,
self-updating pitfall catalog, rewrite/`--fix`, HTML dashboard, and shipping as a
Spec-Kit extension. See
[`docs/`](docs) and the design plan for details.

## License

MIT
