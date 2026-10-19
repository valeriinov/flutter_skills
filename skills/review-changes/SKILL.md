---
name: review-changes
description: 'Review uncommitted changes via the code-reviewer agent: naming, approach, simplicity, theme. Use for "сделай ревью", "проанализируй изменения", "review my changes".'
argument-hint: "[ optional focus, e.g. file or concern ]"
---

Run the `code-reviewer` agent on the uncommitted changes; it is listed as
`<plugin>:code-reviewer` when installed as a plugin. If no such agent is
available, do the review inline by the same criteria and say so. Append to its
task:
pay special attention to (1) naming consistency of entities, fields, methods
with existing project vocabulary — cite the precedent files; (2) consistency
of approach with project patterns; (3) whether anything can be simplified;
(4) values extracted from theme extensions, not local constants.
The project `AGENTS.md`/`CLAUDE.md` "Review Conventions" and "Naming
Conventions" sections, or the documents they point to, are mandatory context — read them first and obey their
restraint rules. A focus the user named along with the request — a file, a
concern — goes into the same task.

Then verify each finding against the actual code before relaying it — the
reviewer can be wrong. Drop the ones that do not hold, naming in one line which
and why. Relay the survivors in Russian in the agent's own form: verdict line,
then findings. No retelling of the diff, no added summary. Nothing left → одна
строка. Do not apply fixes until the user confirms.

Once confirmed, record a snapshot — `git stash create` (empty output → `HEAD`)
— and the list `git ls-files --others --exclude-standard`, then fix every
finding the user confirmed, Minor included, yourself; spawn up to 4 workers only when
there are more findings than you fix yourself. Then one
re-review: one `code-reviewer` over `git diff <snapshot>` plus, read whole, the
untracked files the fix created (absent from that list) or edited, Significant
and above; verify and fix what it finds, no third round.
