# CLAUDE.md

@AGENTS.global.md

## Personal additions

### Rules from retrospectives

Rules proposed from retrospectives or usage reports need recurrence evidence:
2+ sessions or memories. One-off incident → no rule. Recurring but local → the
rule goes into the skill/file where it bit, not into global instructions. No
new skill for a rarely-performed operation.

### Git

- Never add a `Co-Authored-By` trailer to commit messages unless the user
  explicitly asks for it.

### Communication

- Never use "сиблинг" in dialogue, nor "sibling"/"siblings" in code, comments,
  Dartdoc, markdown or commit messages (any project). Russian: "соседний
  файл/класс", "рядом лежащий", "однотипный", "аналогичный". English: name the
  relation itself — "the neighbouring file/class", "the other five statuses",
  "both root-level routes", "everything else in this folder".

### Output Shape

The `i-have-adhd` ruleset (injected by its SessionStart hook) shapes every prose the user reads —
dialogue, plans, reports. It reaches only the main thread; subagents carry their own output rules.

- It sets form, not language: replies to Russian stay Russian (§5).
- §1 assumptions go after the first action line — two lines max, or one clarifying question.
- Code, commit messages, and Dartdoc stay normal prose.
- Subagent prompts and agent-to-agent output stay caveman-compressed (`cavecrew-*`).
- Plan file: Context ≤3 lines, one step = `action → verify: check`, files as a `path | change`
  table, ~40 lines max. No codebase retelling, no rejected alternatives, no prose replay of the
  plan in chat after `ExitPlanMode`.
- A harness mandate fixes which sections exist, not how long they are. Full length only when asked
  to explain — a follow-up question is not that ask. No time estimates at all unless asked outright
  (this overrides the ruleset's rule 6). Progress restated in one clause, never duplicating a task
  checklist.
- Verify a subagent's findings, then relay what survives in its own form — never retell it as prose.
- A run that goes quiet is a run the user interrupts. Before a stretch that will hold the
  turn — a workflow, a fan-out, a long device or lint loop — say in one line what is
  running and what will end it; while it runs, surface each round's result as it lands
  rather than banking them for a final report. "Still working" is not a signal; the
  round number and what it found is.

### Review Routing

- "Ревью PR #N" / "просмотри PR" / "сверь правки по PR" → the `review-pr` skill
  (branch diff + document the user pastes back as comments). `review-changes`
  stays for the working tree.
- `caveman-review` is an output format, not a review depth — use it only on an
  explicit `/caveman-review`.
- `cavecrew-reviewer` — only when explicitly asked to save context / use
  cavecrew.
- "Имплементируй план" / "сделай ревью плана" go to the same skills also when the
  request adds "ultracode".

### Skills and agents

- `~/.claude/skills/` is canonical and symlinked into `~/.agents/skills/` (all but
  `export-flutter-skills`), so one body serves both sides and carries nothing only one
  side expands: spell out "the path you were given" instead of `$ARGUMENTS` (the argument
  is appended even without the placeholder).

@RTK.md
