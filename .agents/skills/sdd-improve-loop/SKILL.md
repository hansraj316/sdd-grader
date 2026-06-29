---
name: sdd-improve-loop
description: One iteration of the SDD-Reviewer self-improvement loop — merge green PRs, research SDD frameworks, implement one improvement behind an objective gate, open a PR. Read this before every run.
---

# SDD-Reviewer Improvement Loop

You are the **improvement loop** for the `sddreview` project. Each run you do a small,
safe amount of work and stop. You have **no memory** between runs — the state file is
your only memory. The objective gate (CI + the benchmark script) decides quality, **not
your own judgment**. Never mark work done because you "think" it's done.

## Hard rules (never violate)

- **One new feature per run**, max. Keep PRs small and single-purpose.
- **Max 3 open `loop/*` PRs at once.** If 3 are open, do merges + state only, then stop.
- **Only auto-merge a PR when GitHub CI reports green** (`gh pr checks` all pass) AND it
  is mergeable. CI — not you — is the grader. A red or pending check = do not merge.
- **Never** `git push --force`, never weaken `.github/workflows/ci.yml`, never merge a PR
  with failing/missing checks, never delete branches you didn't create, never `rm -rf`.
- Touch `main` directly only for the **state file and `reports/`** (and squash-merges).
- If the gate fails and you can't fix it this run: abandon the branch, mark the idea
  `blocked` with the reason in the state file, and stop. A failed attempt is fine; a
  merged regression is not.

## Setup (cloud run starts from a fresh clone)

```
uv venv --python 3.11
uv pip install -e ".[dev]"
```

## Procedure (do these phases in order, then stop)

### Phase 0 — Sync
`git fetch origin && git checkout main && git pull --ff-only`.

### Phase 1 — Merge PRs that CI has turned green
For each open PR from a `loop/*` branch (`gh pr list --search "head:loop/" --json number,headRefName,mergeable`):
- `gh pr checks <n>` — if **all checks pass** and the PR is mergeable:
  `gh pr merge <n> --squash --delete-branch`.
- Record the merge in the state file's "Merged" log.
- If checks are pending, leave it; if failing, comment what failed and leave it (do not merge).

### Phase 2 — Decide whether to build this run
- Count open `loop/*` PRs. **If ≥ 3, skip to Phase 7** (state + stop).
- **The backlog is GitHub issues labeled `loop-candidate`.** List them:
  `gh issue list --label loop-candidate --state open --json number,title,body`.
  These are the actionable candidates (`reports/IMPROVEMENT-STATE.md` is now a mirror +
  run-log). If any open issues exist, skip Phase 3 and go to Phase 4.

### Phase 3 — Research (only when < 3 open `loop-candidate` issues, or every 5th iteration)
Fan out **sub-agents in parallel**, one per SDD framework, each returning concrete
features `sddreview` lacks. Cover at least: **OpenSpec, Spec-Kit extensions/presets,
AIDE, Canon, MAQA, Kiro, Tessl**, plus requirements-engineering practice (ISO/IEC/IEEE
29148, INVEST, Gherkin, IBM RQA, QVscribe, EARS). Each sub-agent answers: "What concrete,
detectable spec-quality check or reviewer feature does this framework suggest that
sddreview does not yet have?" For each **new, de-duplicated** idea (check it against open
AND closed `loop-candidate` issues first), **create a GitHub issue**:
`gh issue create --label loop-candidate,enhancement --title "..." --body "what/why/source/acceptance"`.
If two consecutive research rounds create no new issues, set `STATUS: NOTHING-TO-IMPROVE`.

### Phase 4 — Implement ONE improvement
- Pick the highest-value open `loop-candidate` issue. Note its number `#N`.
- `git checkout -b loop/<short-slug>`.
- Implement it: code + tests + docs, following the issue's Acceptance section. Prefer
  extending the pitfall catalog (`sddreview/rubric/pitfalls.toml`) and
  `engine/lint.py`/`engine/judge.py`, adding an adapter, or a report/dashboard feature.
  Keep it focused — one issue per PR.

### Phase 5 — Objective gate (must pass before any PR)
```
uv run pytest -q
uv run python scripts/benchmark.py     # writes reports/benchmarks/latest.json
```
Both must exit 0. The benchmark must still show good==100, bad<70, and the key pitfalls
tripping. If either fails and you cannot fix it cleanly: `git checkout main`, abandon the
branch, mark the idea `blocked`, go to Phase 7.

### Phase 6 — Open a PR (do NOT merge here)
- Commit (Co-Authored-By trailer), `git push -u origin loop/<slug>`.
- `gh pr create --title "..." --body "what + why + how tested. Closes #N"` — the
  **`Closes #N`** line auto-closes the `loop-candidate` issue when the PR squash-merges.
- Comment on the issue: `gh issue comment N --body "Implemented in PR #<pr>; awaiting CI."`
- CI runs on the PR. It will be merged in a **future** run's Phase 1 once green.

### Phase 7 — Update state and stop
- Update `reports/IMPROVEMENT-STATE.md`: bump iteration, move the idea to "In PR" (with
  PR link) or "Blocked"/"Merged", and append a one-line run summary with the date.
- `git checkout main`, commit the state + `reports/` changes, `git push origin main`.
- Stop. Do not start another feature this run.

## Stop conditions (the loop is "done")
Write `STATUS: NOTHING-TO-IMPROVE` at the top of the state file when **all** hold:
- No open `loop-candidate` issues remain, AND
- Two consecutive research rounds created no new issues, AND
- No open `loop/*` PRs remain.

While in that state the routine still fires but should no-op (Phase 0–1 only). The user
(or anyone) can wake it up by **opening a new issue labeled `loop-candidate`**.

## Autonomy
Level 4 (auto-merge on green CI), explicitly chosen by the user. The independent grader
is GitHub Actions CI (`.github/workflows/ci.yml`: pytest + benchmark gate). The loop
never merges on its own claim — only on CI's green verdict.
