---
name: make-plan
description: Draft an implementation plan via the full pipeline — scout agents mine codebase precedent, plan written to plan/<name>.md, auto-reviewed by plan-reviewer. Use for "составь план", "подготовь план", or before non-trivial changes.
argument-hint: [ task description (optionally: plan file name) ]
---

Build an implementation plan for: $ARGUMENTS (if the placeholder is not
expanded, take the task from the user's request).

Requires the `plan-reviewer` agent — install it with `/setup-flutter-skills`.
If it is not available, do step 3 inline against the same criteria instead of
dispatching, and say so in the report.

## 1. Scout

Launch 1-2 parallel `Explore` agents (2 only when the task spans multiple
areas). Each must return, with `file:line` references:
- existing implementations of similar features (the closest precedent to copy);
- existing utilities/helpers/base classes to reuse instead of writing new code;
- the naming vocabulary of the affected layer (sibling classes, methods,
  suffix/prefix families).

## 2. Draft

Write the plan to `plan/<kebab-name>.md` (create `plan/` if missing; use the
name from the task description if one was given). Sections — proportional to the task, skip a
section rather than pad it:

- `## Context` — why this change; problem and intended outcome.
- `## Assumptions & Evidence` — only if the plan relies on claims about
  runtime behavior, data shape, or external systems. Each entry:
  the assumption + its evidence (`file:line` trace, doc, or an explicit
  verification step). An assumption without evidence is a blocker: verify it
  now or mark the plan blocked on it.
- `## Naming` — only if new public identifiers are introduced. Each name +
  1-2 precedents from the scout results.
- `## Steps` — each step paired with its verify check
  (`[step] → verify: [check]`).
- `## Verification` — end-to-end check: lint/analyze, tests, manual run.

## 3. Review

Run the `plan-reviewer` agent on the plan file (pass path + content). Apply
its Blocking/Significant fixes to the file; list Minor ones for the user to
decide.

## 4. Report

In Russian: the final plan summary, the reviewer's verdict, applied fixes,
and open questions (unverified assumptions, rejected Minor findings). Do not
start implementing — that is `implement-plan`'s job.