---
name: make-plan
description: Draft an implementation plan — scout codebase precedent, write plan/<name>.md, auto-review it. Use for "составь план", "подготовь план", "make a plan", or before non-trivial changes.
argument-hint: "[ task description (optionally: plan file name) ]"
---

Build an implementation plan for the task you were given; ask if none is given.
A trailing file name, if any, names the plan file.

## 1. Scout

Launch 1-2 parallel read-only exploration agents (`Explore` in Claude Code; 2
only when the task spans multiple areas). Each must return, with `file:line` references:
- existing implementations of similar features (the closest precedent to copy);
- existing utilities/helpers/base classes to reuse instead of writing new code;
- the naming vocabulary of the affected layer (neighbouring classes, methods,
  suffix/prefix families).

## 2. Draft

Write the plan to `plan/<kebab-name>.md` (create `plan/` if missing; use the
file name from the request if one was given). Sections — proportional to the task, skip a
section rather than pad it:

- `## Context` — ≤3 lines: the problem and the intended outcome, no backstory.
- `## Assumptions & Evidence` — only if the plan relies on claims about
  runtime behavior, data shape, or external systems. Each entry:
  the assumption + its evidence (`file:line` trace, doc, or an explicit
  verification step). An assumption without evidence is a blocker: verify it
  now or mark the plan blocked on it.
- `## Naming` — only if new public identifiers are introduced. Each name +
  1-2 precedents from the scout results.
- `## Steps` — one line per step: `[step] → verify: [check]`. Files go in a
  `path | what changes` table, not per-line enumeration.
- `## Verification` — end-to-end check: lint/analyze, tests, manual run.

Ceiling ~40 lines. Over it, cut detail, never steps. No retelling of the
codebase, no walkthrough of rejected alternatives.

## 3. Review

Run the `plan-reviewer` agent on the plan file (pass path + content); it is
listed as `<plugin>:plan-reviewer` when installed as a plugin. If no such agent
is available, do the review inline by the same criteria and say so. Apply its
Blocking/Significant fixes to the file; list Minor ones for the user to decide.

## 4. Report

In Russian, one line each: путь к плану, вердикт ревьюера, применённые правки,
открытые вопросы (unverified assumptions, rejected Minor findings). Не
пересказывать план прозой. Do not start implementing — that is
`implement-plan`'s job.