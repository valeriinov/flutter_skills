---
name: review-plan
description: Review a plan file via the plan-reviewer agent; result in Russian.
  Use for "проанализируй план plan/X.md".
argument-hint: [ path to plan file ]
---

Requires the `plan-reviewer` agent — install it with `/setup-flutter-skills`.
If it is not available, run the review inline against the same criteria instead
of dispatching, and say so in the report.

Run the `plan-reviewer` agent on the plan at $ARGUMENTS (if the placeholder is
not expanded, take the plan path from the user's request; pass both the file
path and its content). Append to its task: audit the plan's assumptions —
every claim about runtime behavior or data must carry evidence (file:line
trace or verification step); flag each unbacked one.

Then: summarize the verdict and findings in Russian, propose
concrete plan improvements only if needed, and ask whether to update the plan
file with the accepted changes.
