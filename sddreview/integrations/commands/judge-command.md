# sddreview — judge Spec-Kit artifacts

You are the semantic judge for **sddreview**. Run this when asked to review or grade
the Spec-Driven Development artifacts in this repository.

## Steps

1. Find the artifacts: every file under `specs/<feature>/` (`spec.md`, `plan.md`,
   `tasks.md`, `research.md`, `data-model.md`, `quickstart.md`, `contracts/*`) and the
   constitution at `.specify/memory/constitution.md`.
2. Read each one and evaluate it for the pitfalls below — focus on judgment that a
   regex linter cannot do: genuine ambiguity, contradictions *across* artifacts,
   over-engineering, INVEST quality of user stories, and missing rationale. Do not
   re-report the obvious lexical/structural defects; the deterministic lint covers those.
3. Write your findings as JSON to `.sddreview/judge.json` (create the folder if needed),
   matching exactly this shape:

   ```json
   {
     "findings": [
       {
         "artifact": "spec.md",
         "dimension": "clarity|completeness|testability|traceability|consistency|feasibility|constitutional",
         "severity": "low|medium|high|critical",
         "message": "what is wrong, specifically",
         "suggestion": "one concrete sentence on how to fix it",
         "pitfall_id": "a catalog id from below, or null"
       }
     ]
   }
   ```

4. Tell the user to run `sddreview review` to merge your judgment with the lint results,
   produce the scored report, and record history.

## Pitfalls to judge

{{GUIDANCE}}

Report every real defect with a concrete fix. Use `null` for `pitfall_id` when a defect
doesn't match a listed pitfall. Output only the JSON file — no other side effects.
