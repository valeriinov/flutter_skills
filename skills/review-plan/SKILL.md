---
name: review-plan
description: Review a plan file via the plan-reviewer agent; result in Russian. Use for "проанализируй план plan/X.md", "сделай ревью плана", "review the plan".
argument-hint: "[ path to plan file ]"
---

Run the `plan-reviewer` agent on the plan file at the path you were given (ask
if none is given); pass both the file path and its content. The agent is listed
as `<plugin>:plan-reviewer` when installed as a plugin; if no such agent is
available, do the review inline by the same criteria and say so. Append to its
task: audit the plan's assumptions —
every claim about runtime behavior or data must carry evidence (file:line
trace or verification step); flag each unbacked one.

Then verify each finding against the plan and the code — the reviewer can be
wrong. Drop the ones that do not hold, naming in one line which and why. Relay
the survivors in Russian in the agent's own form, without retelling the plan.
End with one question: обновить ли план-файл принятыми правками.
