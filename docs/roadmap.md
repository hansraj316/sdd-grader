# Roadmap

Phase 1 (shipped): Spec-Kit artifact reviewer — hybrid lint + agent judge, fix
suggestions, pitfall catalog, history, terminal dashboard, advisor, CI gate.

Planned:

- **OpenSpec adapter** — a second `ArtifactAdapter`; `--tool openspec` / auto-detect.
- **Tool-vs-tool benchmark** — score Spec-Kit vs OpenSpec output for the same intent.
- **Self-updating pitfall catalog** — a scheduled loop that watches upstream Spec-Kit /
  OpenSpec releases and re-runs the pitfall research to refresh `rubric/pitfalls.toml`.
- **Rewrite proposals & `--fix`** — generate improved sections and optionally write them.
- **HTML dashboard** — a shareable export of the terminal metrics view.
- **Ship as a Spec-Kit extension/preset** — installable via `specify extension add`.
- **Alternative SDD methodologies** — adapters for AIDE, Canon, MAQA, etc.

See the design plan for the full rationale.
