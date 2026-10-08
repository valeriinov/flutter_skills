---
name: make-plan
description: Draft a plan from plan/<name>/inputs/ with gate, auto-review and plan.html; revise mode answers comments. Use for "составь план", "make a plan", "доработай план по комментариям".
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
| brief and contract review | `visual-reviewer` (`<plugin>:visual-reviewer` as a plugin) | `explorer` with the visual-reviewer criteria, told to read only the JSON and its source (no Codex role is code-blind, so the prompt carries the restriction) |

## Graph

Longest agent path: extractor → scout → reviewer (3 of the 5-agent cap; the reviewers run in
parallel, so all sit on its last node); never add a node to it.

1. **Intake** — list `plan/<name>/inputs/`. No folder → the task text is the only input.
2. **Extract** — only if inputs hold non-code (screenshots, text, links): one extractor agent
   returns distilled requirements → `## Requirements`, ≤10 lines.
3. **Scout ∥ Contract**, in parallel:
   - Scout: 1–2 read-only agents (2 only when the affected features span areas); input = the
     affected features. Each returns with `file:line`: the closest precedent to copy, utilities to
     reuse, the naming vocabulary of the affected layer.
   - Contract: only if a backend input exists → run the `backend-contract` skill, then the
     `visualize` skill's Model, Write, Trace and Check steps on its document (no review of its
     own: step 6 reviews it). `## Contract` links the document; the Контракт tab draws
     `<document stem>.visual.json` beside it. Never rewrite the document.
4. **Draft** `plan/<name>/plan.md` for the agent and `plan/<name>/brief.json` for the reader; front
   matter always carries `lane:` (contained | wide | closed).
5. **Gate** — `python3 plan_tool.py check <plan.md>` must exit 0; it checks `brief.json` and the
   contract JSON too. Fix each reported line, rerun;
   after 3 failed runs stop and report the remaining violations.
6. **Review**, depth by lane (missing → wide): contained → inline, one pass by the plan-reviewer and
   visual-reviewer criteria; wide/closed → `plan-reviewer` and `visual-reviewer` in parallel, each
   in a fresh context — the visual reviewer once for `brief.json` with `plan.md` as its source, and
   once more for the contract JSON with the contract document as its source when there is one (pass
   both paths + contents, plus the task text and `## Requirements` when extracted). Verify each plan
   finding against the plan and the code, each visual finding against its JSON and its source;
   drop the ones that do not hold.
7. **Correct** — apply Blocking/Significant fixes to the flagged steps only, one round, then rerun
   the gate. Minor findings go to the report for the user to decide.
8. **Render** — `python3 plan_tool.py render <plan.md>`, then start
   `python3 plan_tool.py serve <plan.md>` as a background process: it opens the plan in the
   browser, every comment and option pick is appended to the comments file at once,
   and "Отправить ревью" stops the server with `review submitted: <n> open comments`. Open
   comments can be edited or deleted on the page before submitting.
   - No open comments → the button becomes "Имплементировать план": it opens one new terminal
     window — Ghostty (1.3+, via its AppleScript) when installed, Terminal.app otherwise — with a
     separate Claude Code session running `implement-plan` with subagents, and `serve` exits with
     `implementation started` → stop and report that implementation runs in that window; no
     Revise. macOS only — elsewhere the page shows the error and the user starts
     `implement-plan` themselves.
   - n > 0 → Revise mode. The page shows "Агент правит план…" and reloads on every change to
     the plan, brief or comments file while `serve` runs.
   - n = 0, or the process ends any other way → stop and report.
   - A harness that does not wake you when a background process exits: tell the user to say
     "доработай план по комментариям" after submitting.
   - `serve` reuses the port recorded in `serve-port` beside the comments file, else takes the
     next free one in 8790–8799; all busy → the error names the range; stop another `serve` or
     pass `--port`.
   - `already served: <url>` (exit 3) → this plan already has a running `serve`; the page is
     opened there. Stop and tell the user to say "доработай план по комментариям" after submitting.
   - The page stuck on "Агент правит план…" after the revising `serve` died → run
     `open-plan.command`.
   `render` also writes `open-plan.command` beside the plan: double-clicking it (or running it)
   starts `serve` again after the page was closed.
   Dictation in the comment popup and in comment edits (macOS): the page streams audio to `serve`,
   which transcribes it on device and returns the text live; on first use it builds `PlanDictation.app` from `dictation.swift` into the user's
   caches, and macOS asks once for speech-recognition permission.
   Publishing `plan.html` gives a read-only page (no comments, no submit).

## Draft rules

- A backend contract, ticket or design decides what happens and the wire shape, never how the
  client does it: steps follow the scout's precedent; names and error handling are the project's.
  Each departure is an open question with two options — the project's way / the input's.
- An assumption without evidence (`file:line` or `verify:`) is a blocker: verify it now or mark
  the plan blocked on it. A claim about a package or SDK API's behaviour cites the line in
  that package's own source (pub cache, package sources), never the project's call site or memory
  of the API. `## Naming` only for new public identifiers, 1–2 precedents each.
- Step: `### S<n> · <what changes and why, plain words>`, then one agent line
  `` `path/or/Symbol` — <exact change> → verify: <check> ``, then
  `<details><summary>Evidence</summary>` with the `file:line` trail. Ceiling ~12 step headings;
  evidence is uncounted. No codebase retelling, no rejected alternatives.
- **brief.json** — the reader's page: a `visualize` document (read that skill's `SKILL.md` for the
  page model, the shape and the writing rules) built from `plan.md`, `"lang": "ru"`, plain Russian.
  `check` runs visualize's checks plus these:
  - Every section carries `"steps": ["S1", "S2"]` — every plan step in exactly one section — and
    `"check"`: how the result is observed, one sentence.
  - No `file:line` or step id anywhere the reader sees; files go only in `files`.
  - Open questions live only in `questions`; the page shows each option as a button.
- **brief.json writing** — for a reader who has not seen the code; the visual reviewer checks it:
  - The overall diagram answers "what changes and where": every entity the plan creates or changes
    is on it, and its arrows show who calls or feeds whom.
  - A section's `title` is the result in plain words, its `takeaway` the conclusion, its diagram
    the change it makes; `lines` hold only how it is today and what the diagram cannot carry.
  - A question's `gist` is understandable without the code: what is being decided, why it needs
    deciding and what it affects, with a concrete example.
  - A term the reader may not know is replaced or explained on first use (`clarity` law 12).
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

Comments file: `comments.md` beside `plan.md`. A line is `- [ ] [<S3 | T2 | Пункт 2 | Вопрос 1 |
Схема | section>] «<quote>» @<name>: <text>`; quote and name are optional. Read the open `- [ ]`
items. For each: edit only the addressed step, section or question (the quote pins the spot) — in
`brief.json` and `plan.md` together whenever the change touches both. `Пункт <n>` is the n-th
entry of `sections`, `Вопрос <n>` the n-th of `questions`:
- `Выбран вариант <key>` or `Свой вариант: <text>` on `Вопрос <n>` is the answer → apply it to the
  affected sections and steps and remove the question from `questions`; the last pick or free
  answer per question wins, earlier ones are marked `[x]` without a reply.
- `[Схема] «<node label>»` or `«<from> → <to>»` → edit that node or arrow of the overall `flow`
  (or `entities`/`links`) in `brief.json`, and the matching sections and steps.

Mark each `[x]`, add an
indented reply `  - @<agent>: <what changed>`. Re-scout only when a
comment demands new facts.

Order, so the user watches the edits land: first start `python3 plan_tool.py serve <plan.md>
--no-open --revising` in the background (the page shows the agent at work), then edit, then gate
(step 5) and render, then `python3 plan_tool.py revised <plan.md>` (same `--port` as `serve`, if any) — the button returns and the
running `serve` waits for the next submit as in step 8.

## Report

In Russian, one line each: URL открытой страницы, путь к open-plan.command и пути к brief.json и plan.md, вердикт ревьюера, применённые правки,
открытые вопросы (unverified assumptions, rejected Minor findings). If a comment class repeats
across 2+ plans, propose it as an instruction rule — never write a rule directly. Не
пересказывать план прозой. Do not implement — that is `implement-plan`'s job.
