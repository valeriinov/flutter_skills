---
name: implement-plan
description: Analyze and implement a plan file, then verify. Use for
  "имплементируй план plan/X.md".
argument-hint: '[ path to plan file (optionally: step number) ]'
---

Step 5 requires the `code-reviewer` agent — install it with
`/setup-flutter-skills`. If it is not available, run that review inline against
the same criteria instead of dispatching, and say so in the report.

1. Read the plan at $ARGUMENTS (if the placeholder is not expanded, take the path from the user's request). If it names steps and the user specified one,
   do only that step.
2. Before editing, verify the plan's file references still exist; flag drift.
3. Implement exactly what the plan says — no scope creep.
4. Verify: if the project has a lint skill use it, otherwise run
   format + analyze + tests for the stack. Fix until clean.
5. Run the `code-reviewer` agent on the diff, passing the plan file path and
   content — ask it to check plan compliance (every planned step implemented,
   nothing beyond plan scope) alongside its normal criteria. Fix Blocking
   findings; list the rest.
6. Report in Russian: what was done, verification results, reviewer verdict,
   deviations from plan. End with a single offer to commit — never commit
   without confirmation.
