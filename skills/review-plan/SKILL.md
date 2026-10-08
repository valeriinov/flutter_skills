---
name: review-plan
description: Review a plan file via the plan-reviewer agent; result in Russian. Use for "проанализируй план plan/X.md", "сделай ревью плана", "review the plan".
argument-hint: "[ path to plan file ]"
---

The path you were given is a plan file or a plan folder `plan/<name>/` — then
review its `plan.md`; ask if none is given. First run
`python3 ~/.claude/skills/make-plan/plan_tool.py check <plan.md>`; relay each
failure it prints as a 🔴 Blocking finding. Run the `plan-reviewer` agent on the
plan file and, when it exists, the `brief.json` beside it; pass each path and its content. The agent is listed
as `<plugin>:plan-reviewer` when installed as a plugin; if no such agent is
available, do the review inline by the same criteria and say so. Append to its
task: audit the plan's assumptions —
every claim about runtime behavior or data must carry evidence (file:line
trace or verification step); flag each unbacked one. When `brief.json` exists, run
the `visual-reviewer` agent (`<plugin>:visual-reviewer` as a plugin) in parallel
on `brief.json` with `plan.md` as its source, passing each path and its content;
without that agent, apply its criteria inline and say so.

Then verify each finding — plan findings against the plan and the code, brief
findings against `plan.md` and `brief.json` — the reviewers can be wrong. Drop the ones that do not hold, naming in one line which and why. Relay
the survivors in Russian in the agents' own form, without retelling the plan.
End with one question: обновить ли план-файл принятыми правками. If the user
agrees, apply them, then run `plan_tool.py render <plan.md>` to refresh the HTML.
