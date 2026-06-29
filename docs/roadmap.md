# Roadmap

Phase 1 (shipped): Spec-Kit artifact reviewer — hybrid lint + agent judge, fix
suggestions, pitfall catalog, history, terminal dashboard, advisor, CI gate.

Planned:

- **OpenSpec adapter** — ✅ early support (auto-detect + `--tool openspec`). Next:
  delta semantics (`## ADDED/MODIFIED/REMOVED Requirements`), archive handling.
- **Tool-vs-tool benchmark** — score Spec-Kit vs OpenSpec output for the same intent.
- **Self-updating pitfall catalog** — a scheduled loop that watches upstream Spec-Kit /
  OpenSpec releases and re-runs the pitfall research to refresh `rubric/pitfalls.toml`.
- **Rewrite proposals & `--fix`** — generate improved sections and optionally write them.
- **HTML report** — ✅ `--html` writes a self-contained findings + fixes report. Next:
  an HTML *dashboard* (score trends across history), not just a single-run report.
- **Ship as a Spec-Kit extension/preset** — installable via `specify extension add`.
- **Alternative SDD methodologies** — adapters for AIDE, Canon, MAQA, etc.

See the design plan for the full rationale.
