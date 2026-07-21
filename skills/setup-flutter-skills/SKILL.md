---
name: setup-flutter-skills
description: Install the parts of the flutter_skills repo that `npx skills` cannot — the code-reviewer and plan-reviewer subagents, and the project AGENTS.md template. Use after installing the skills, or for "доустанови агентов", "finish the install", "install the subagents", "setup flutter skills".
argument-hint: '[ optional: global | project ]'
allowed-tools: Bash, Read, Write, Glob
---

`npx skills` installs skills and nothing else. Four skills in this repo —
`make-plan`, `review-plan`, `review-changes`, `implement-plan` — dispatch to the
`code-reviewer` / `plan-reviewer` subagents, which the CLI never places. This
skill installs them.

Source of truth (branch `main`):
`https://raw.githubusercontent.com/valeriinov/flutter_skills/main/`

## 1. Scope

Read it from $ARGUMENTS (if the placeholder is not expanded, take it from the
user's request). Accepted: `global` → `~/.claude/`, `project` → `./.claude/`.
If neither is given, ask. Default to `global` — these agents are workflow-wide,
not project-specific.

## 2. Subagents

Fetch into `<scope>/agents/`, creating the directory if missing:

```bash
BASE=https://raw.githubusercontent.com/valeriinov/flutter_skills/main
curl -fsSL "$BASE/claude/agents/code-reviewer.md" -o <scope>/agents/code-reviewer.md
curl -fsSL "$BASE/claude/agents/plan-reviewer.md" -o <scope>/agents/plan-reviewer.md
```

`-f` is required: without it a 404 writes an HTML error page into the agent
file, which then silently fails to load.

**Before writing, check whether the target already exists.** If it does, fetch
to a temp path, diff it against the current file, and ask the user before
overwriting — a customized agent must never be clobbered silently. Identical
files need no prompt; report them as already current.

## 3. Project AGENTS.md

Only when scope is `project`, or when the user asks for it.

If the project root has no `AGENTS.md`, offer to seed it from
`$BASE/templates/AGENTS.project.md`. If one already exists, do not touch it —
say so and move on; merging is the user's call, not this skill's.

`templates/AGENTS.global.md` is reference material for personal `~/.claude/CLAUDE.md`
setup. Point the user at it; never write it anywhere.

## 4. Report

State plainly, without claiming more than was verified:

- which subagents landed, and which were left alone because they already matched;
- which of the 8 companion skills are visible (`ls <scope>/skills/` or the
  agent's own skill list) and which are missing;
- whether `AGENTS.md` exists in the project root.

List what is still missing. Do not report success for a step that did not run.

## Failure path

If `curl` exits non-zero — offline, blocked network, repo renamed, branch
renamed — stop and print the manual fallback. Do not retry silently and do not
leave a partial file behind:

```bash
git clone https://github.com/valeriinov/flutter_skills.git
cp flutter_skills/claude/agents/*.md ~/.claude/agents/
```

## Known limitation

The URLs are pinned to `main`, so this always fetches the newest subagents
regardless of which version of the skills is installed — the two can drift apart.
Acceptable because the agents are self-contained prompt files with no version
contract against the skills. But a repo rename, an owner rename, or a default
branch rename breaks every installed copy of this skill, and the only fix is
reinstalling it.