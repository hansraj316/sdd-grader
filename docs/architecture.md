# Architecture

`sddreview` is a small, layered Python package. Each layer has one job and a clean
interface, so the engine is adapter-agnostic and new toolchains (OpenSpec) or judge
backends are additive.

```
cli → runner → { discovery → adapter } → engine(lint + judge) → scoring → report + history
```

| Module | Responsibility |
|--------|----------------|
| `cli.py` | Five plain commands (Typer): `init`, `review`, `advise`, `dashboard`, `self`. |
| `runner.py` | Orchestrates one review: discover → lint → judge → score → report → history. |
| `discovery.py` / `adapters/` | Detect a toolchain's layout and normalize artifacts. `speckit.py` today; OpenSpec later. |
| `model.py` | The shared data model (`Artifact`, `Finding`, `DimensionScore`, `ReviewResult`). |
| `catalog.py` / `rubric/pitfalls.toml` | The research-backed SDD pitfall catalog. |
| `engine/lint.py` | Deterministic checks (sections, lexical pitfalls, structural + cross-artifact). |
| `engine/judge.py` | Semantic judging via a `JudgeBackend`; yields more findings. |
| `integrations/` | `agent.py` (default — the user's agent, no key) and `api.py` (optional, key-based). |
| `engine/scoring.py` | Findings → per-dimension 0-100 + penalty-weighted overall. |
| `report/` | Terminal (rich), Markdown, JSON, SARIF, and self-contained HTML renderers. |
| `history.py` / `dashboard.py` | Append-only JSONL trail and a terminal metrics view. |
| `advisor.py` | Heuristic SDD-adoption recommendations for a codebase. |

## Scoring

Every dimension starts at 100 and loses points per finding by severity (critical 25,
high 12, medium 6, low 2). An artifact's overall is `100 − total weighted penalty`
(penalty-based, not an average of dimension scores — so real defects aren't diluted by
dimensions that happen to be clean). The run overall weights the core trio
(spec/plan/tasks) above supporting docs.

## Judge backends (the Spec-Kit model)

The semantic judge runs in the user's existing agent subscription. `init --integration`
scaffolds a slash command; the agent writes `.sddreview/judge.json`; `review` merges it.
No API key. `--api` is an opt-in key-based path for CI; `--rules` skips the judge.
