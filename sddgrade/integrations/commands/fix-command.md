---
description: Fix the top sddgrade findings in the SDD artifacts, re-run the review, and report the before/after score delta.
---

# sddgrade — fix top findings

Apply fixes for the highest-impact sddgrade findings, then prove the improvement
with a before/after score.

## User input

```text
$ARGUMENTS
```

If the input names a number, fix that many findings; otherwise fix the top 3. If it
names specific artifacts or dimensions, restrict fixes to those.

## Steps

1. Run `sddgrade review --json` from the repository root and record the overall
   score as the **before** score. (If it reports the judge unavailable or stale,
   follow `/sddgrade.judge` first so the score includes semantic findings.)
2. Pick the top N findings from the JSON, worst severity first. Prefer findings
   whose `fix` object is non-null — it carries structured, machine-applicable data
   (`kind`: `resolve-marker` | `insert-section` | `replace-line`, plus
   `line_start`/`line_end`). For the rest, apply the finding's `suggestion`.
3. Edit the artifacts (`spec.md`, `plan.md`, `tasks.md`, …) to resolve each picked
   finding. Preserve intent: resolve ambiguity with a real decision (ask the user
   when the decision is theirs to make), never delete or water down a requirement
   just to silence a finding.
4. The artifacts changed, so re-judge them: follow `/sddgrade.judge` to write a
   fresh `.sddgrade/judge.json`.
5. Run `sddgrade review --json` again and report: before → after overall score,
   which findings were fixed, and the top findings that remain.
