# sddreview

**A CI-grade linter and reviewer for AI-generated [GitHub Spec-Kit](https://github.com/github/spec-kit) artifacts.**

Spec-Kit (and OpenSpec) generate spec-driven-development artifacts — `spec.md`,
`plan.md`, `tasks.md`, a constitution — but nothing in your pipeline tells you whether
a given spec is *good enough to build from*: complete, unambiguous, testable, traceable,
and aligned with its constitution. `sddreview` grades each artifact 0–100 across quality
dimensions, attaches a concrete **fix suggestion** to every finding, flags known **SDD
pitfalls**, tracks score **history**, and **gates CI** — from a simple CLI that installs
and behaves like `specify` itself.

It is honest about what it can prove. A clean **lint-only** score means *no known
deterministic findings* — not that the spec is semantically complete. Turn on the
semantic judge for the deeper review (see Review modes).

## Review modes — and what each one proves

| Mode | How to run | What a high score means |
|------|-----------|--------------------------|
| **Lint-only** (`rules`) | `sddreview review --rules` | No known *deterministic* findings: required sections present, no unresolved `[NEEDS CLARIFICATION]`, traceability intact, no lexical pitfalls. Fast, free, reproducible. **Not** a semantic guarantee. |
| **Agent-judged** (default) | `sddreview review` after `init` | Lint **plus** a semantic review by your own AI agent (ambiguity, contradictions, over-engineering, INVEST). No API key. |
| **API-judged** (`--api`) | `sddreview review --api` | Same semantic review via a key-based API call, for headless CI. |

Every report states its **coverage** (`lint-only` vs `lint+semantic`) so a green CI check
is never mistaken for full validation. Use `--require-judge` to *fail* rather than
silently degrade to lint-only when the judge isn't available.

## How it works

A **hybrid engine**:

- **Deterministic lint** (free, offline, reproducible) — turns Spec-Kit's own
  conventions into measurable signals: unresolved `[NEEDS CLARIFICATION]` markers,
  constitutional gates (Simplicity / Anti-Abstraction / Integration-First / Test-First),
  the traceability chain (story → scenario → task, entity → task, contract → test),
  `[P]` task hygiene, WHAT-not-HOW spec discipline, and a research-backed catalog of
  requirement smells (ambiguity, passive voice, escape clauses, negative/unclear
  requirements, unquantified NFRs).
- **Semantic judge** — runs **inside your existing AI agent** (Claude Code, Copilot,
  Cursor, Gemini…) using the subscription you already have, **no API key**.
  `sddreview init --integration <agent>` scaffolds a slash command; your agent judges
  the artifacts and writes structured JSON back, which the CLI merges and scores. A
  key-based `--api` backend exists for headless CI, and `--rules` runs lint-only.

## Who it's for (and who it isn't)

**Best fit:** teams using Spec-Kit / OpenSpec-style AI workflows on **nontrivial
features**, who keep specs in the repo and want spec quality gated like code quality —
in CI, on PRs, with a tracked trend.

**Weak fit / non-goals:**
- One-off "vibe coding" where no spec is kept — there's nothing to grade.
- Teams that don't commit specs to the repo.
- A replacement for human review or for Spec-Kit's own in-agent `/speckit.analyze` —
  `sddreview` is the *external, scored, CI-gating* complement, not a substitute.
- Proving semantic correctness from lint alone (that needs the judge).

## Install

```bash
uv tool install sddreview --from git+https://github.com/hansraj316/sddreview.git
# or zero-install:
uvx --from git+https://github.com/hansraj316/sddreview.git sddreview review
```

## Commands

```bash
sddreview init --integration claude   # scaffold config + agent judge slash command
sddreview review                      # grade every artifact (lint + agent judgment if present)
sddreview review --rules --json       # offline, machine-readable (good for CI)
sddreview review --fail-under 70      # non-zero exit below threshold (CI gate)
sddreview review --require-judge      # fail instead of degrading to lint-only
sddreview review --sarif out.sarif    # emit SARIF for GitHub code scanning
sddreview review --top-fixes 5        # show the highest-impact fixes first
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

Phase 1 (Spec-Kit) with an OpenSpec adapter in progress. Roadmap: tool-vs-tool
benchmark, a labeled spec corpus, self-updating pitfall catalog, rewrite/`--fix`, HTML
dashboard, and shipping as a Spec-Kit extension. See [`docs/`](docs) for architecture
and roadmap.

## License

MIT
