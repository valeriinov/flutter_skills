---
name: make-plan
description: Draft an implementation plan from plan/<name>/inputs/ with gate, auto-review and plan.html; revise mode answers comments. Use for "составь план", "make a plan", "доработай план по комментариям".
argument-hint: "[ task description (optionally: plan name) | plan path + revise ]"
---

Build an implementation plan for the task you were given; ask if none is given. A trailing name
names the plan folder `plan/<name>/`. "доработай план по комментариям" or a plan path + "revise"
→ Revise mode. The plan format is fixed by `plan_tool.py check`; `plan.html` is only ever
produced by `plan_tool.py render`, never written by hand. Both commands run from this skill's folder.

## Roles

Models are pinned by the role definitions; pick the role, never a model.

| node | Claude Code | Codex |
|---|---|---|
| extractor, scout | `Explore` | `explorer` |
| review | `plan-reviewer` (`<plugin>:plan-reviewer` as a plugin) | `code-reviewer` with the plan-reviewer criteria |

## Graph

Longest agent path: extractor → scout → reviewer (3 of the 5-agent cap); never add a node to it.

1. **Intake** — list `plan/<name>/inputs/`. No folder → the task text is the only input.
2. **Extract** — only if inputs hold non-code (screenshots, text, links): one extractor agent
   returns distilled requirements → `## Requirements`, ≤10 lines.
3. **Scout ∥ Contract**, in parallel:
   - Scout: 1–2 read-only agents (2 only when the affected features span areas); input = the
     affected features. Each returns with `file:line`: the closest precedent to copy, utilities to
     reuse, the naming vocabulary of the affected layer.
   - Contract: only if a backend input exists → run the `backend-contract` skill. `## Contract`
     links its document plus at most one mermaid sequence diagram; never rewrite the document.
4. **Draft** `plan/<name>/plan.md`; front matter always carries `lane:` (contained | wide | closed).
5. **Gate** — `python3 plan_tool.py check <plan.md>` must exit 0. Fix each reported line, rerun;
   after 3 failed runs stop and report the remaining violations.
6. **Review**, depth by lane (missing → wide): contained → inline, one pass by the plan-reviewer criteria;
   wide/closed → the review agent in a fresh context (pass path + content). Verify each finding
   against the plan and the code; drop the ones that do not hold.
7. **Correct** — apply Blocking/Significant fixes to the flagged steps only, one round, then rerun
   the gate. Minor findings go to the report for the user to decide.
8. **Render** — `python3 plan_tool.py render <plan.md>`. For review, the user runs
   `python3 plan_tool.py serve <plan.md>`: it opens the plan in a browser, and a comment on any
   selected text is appended to the comments file. If the harness can publish a page, offer to
   publish `plan.html`.

## Draft rules

- A backend contract, ticket or design decides what happens and the wire shape, never how the
  client does it: steps follow the scout's precedent; names and error handling are the project's.
  Each departure is an open question with two options — the project's way / the input's.
- An assumption without evidence (`file:line` or `verify:`) is a blocker: verify it now or mark
  the plan blocked on it. `## Naming` only for new public identifiers, 1–2 precedents each.
- Step: `### S<n> · <what changes and why, plain words>`, then one agent line
  `` `path/or/Symbol` — <exact change> → verify: <check> ``, then
  `<details><summary>Evidence</summary>` with the `file:line` trail. Ceiling ~12 step headings;
  evidence is uncounted. No codebase retelling, no rejected alternatives.
- **Stages** only if at least one holds: more than one change contract (things the project rules
  require to change together in one commit); a part leaves the build green with its own gate; a
  part needs separate device verification or sits in the closed lane; more than ~8 files across
  layers. Otherwise no `## Stages`. Never split by folder or layer. Each dependency names the
  artifact that crosses it.
- **Worktree** — ask only if stages > 1 or the user said to work in a worktree. Ask the base
  (default: current branch@HEAD) and the branch name; write `base: <branch>@<sha>`, `branch:`,
  `worktree: .worktrees/<name>`. Run `git check-ignore -q .worktrees`; if not ignored, propose
  adding `.worktrees/` to `.gitignore` and stop until the user agrees. Never create the worktree
  (`implement-plan` does). Plan and comments always live in `plan/` of the main tree.

## Revise mode

Comments file: `comments.md` beside `plan.md`. A line is `- [ ] [<S3 | T2 | section>] «<quote>» @<name>:
<text>`; quote and name are optional. Read the open `- [ ]` items. For each: edit only the addressed
step or section (the quote pins the spot), mark it `[x]`, add an indented reply `  - @<agent>: <what
changed>`. Re-scout only when a
comment demands new facts. Then gate (step 5) and render (step 8).

## Report

In Russian, one line each: путь к plan.html и plan.md, вердикт ревьюера, применённые правки,
открытые вопросы (unverified assumptions, rejected Minor findings). If a comment class repeats
across 2+ plans, propose it as an instruction rule — never write a rule directly. Не
пересказывать план прозой. Do not implement — that is `implement-plan`'s job.
