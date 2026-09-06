---
name: implement-plan
description: Implement a plan file step by step, verify, then review the diff. Use for "имплементируй план plan/X.md", "implement the plan".
---

1. Read the plan file the user names; ask for the path if none is given. If it
   names steps and the user specified one, do only that step.
2. Before editing, verify the plan's file references still exist; flag drift.
3. Implement exactly what the plan says — no scope creep.
4. Verify: if the project has a lint skill use it, otherwise run
   format + analyze + tests for the stack. Fix until clean.
5. Run the `code-reviewer` agent on the diff (listed as `<plugin>:code-reviewer`
   when installed as a plugin; if no such agent is available, do the review
   inline by the same criteria and say so), passing the plan file path and
   content — ask it to check plan compliance (every planned step implemented,
   nothing beyond plan scope) alongside its normal criteria. Fix Blocking
   findings; list the rest.
6. Report in Russian, one line each: что теперь работает, результат проверки,
   вердикт ревьюера, отклонения от плана (только если есть). End with a single
   offer to commit — never commit without confirmation.
