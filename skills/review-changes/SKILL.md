---
name: review-changes
description: Review uncommitted changes via the code-reviewer agent with the
  standard emphasis — naming/approach consistency with project patterns,
  simplicity, theme-extension usage. Use when asked to review changes,
  "проанализируй изменения", or before committing.
argument-hint: [ optional focus, e.g. file or concern ]
---

Requires the `code-reviewer` agent — install it with `/setup-flutter-skills`.
If it is not available, run the review inline against the same criteria instead
of dispatching, and say so in the report.

Run the `code-reviewer` agent on the uncommitted changes. Append to its task:
pay special attention to (1) naming consistency of entities, fields, methods
with existing project vocabulary — cite the precedent files; (2) consistency
of approach with project patterns; (3) whether anything can be simplified;
(4) values extracted from theme extensions, not local constants.
The project AGENTS.md "Review Conventions" and "Naming Conventions" sections
are mandatory context — read them first and obey their restraint rules.
Extra focus from the user: $ARGUMENTS (if the placeholder is not expanded, take
any extra focus from the user's request; it is optional).

Then relay findings in Russian, grouped by severity. Propose improvements
only if the review found real issues — otherwise say the change is clean.
Do not apply fixes until the user confirms.
