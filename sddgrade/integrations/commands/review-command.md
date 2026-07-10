---
description: Run a full sddgrade review (judge + lint), present the scored results, and offer to fix the top findings.
---

# sddgrade — review SDD artifacts

Run a full, scored review of this repository's Spec-Driven Development artifacts.

## Steps

1. Run `sddgrade review` from the repository root in the terminal.
2. If the output says the judge is unavailable or the judgment is stale (artifacts
   changed since they were judged), produce a fresh judgment first — follow
   `/sddgrade.judge` (run `sddgrade judge-prompt`, follow its instructions, write
   `.sddgrade/judge.json`) — then run `sddgrade review` again.
3. Present the results to the user:
   - the overall score and whether it passes the configured `fail_under` gate,
   - per-artifact scores,
   - the highest-severity findings, each with its concrete suggestion.
   Need structure? `sddgrade review --json` emits the same report as JSON.
4. Offer to fix the top findings. If the user accepts, follow `/sddgrade.fix`.

Do not edit any artifact during this command — it is read-only reporting; fixes
belong to `/sddgrade.fix`.
