# flutter_skills

Personal AI agent config: skills, subagents, and AGENTS.md conventions.
Flutter-focused, but most of the workflow skills are language-agnostic.

## Install

Two steps. The first installs the skills; the second installs everything the
skills CLI cannot.

```bash
# 1. Skills — all 9
npx skills add valeriinov/flutter_skills --agent claude-code

# 2. Subagents + AGENTS.md template — run inside the agent
/setup-flutter-skills
```

**Why two steps:** [`npx skills`](https://github.com/vercel-labs/skills) is a
package manager for *skills only*. It does not install subagents or `AGENTS.md`.
Four of the skills below dispatch to the `code-reviewer` / `plan-reviewer`
subagents, so a CLI-only install leaves them calling agents that do not exist.
`setup-flutter-skills` fetches those agents from this repo and places them for
you.

## Skills

| Skill | Purpose | Scope | Needs subagent |
|---|---|---|---|
| `setup-flutter-skills` | Installs the subagents and the project AGENTS.md template | — | — |
| `dart-documentation` | Dartdoc for public interfaces and extensions | Dart | — |
| `dart-flutter-tests` | Create, update, or refactor Dart/Flutter tests | Dart/Flutter | — |
| `make-plan` | Draft an implementation plan — scout precedent, write, auto-review | any | `plan-reviewer` |
| `implement-plan` | Implement a plan file, verify, then review the diff | any | `code-reviewer` |
| `review-plan` | Review a plan file before any code is written | any | `plan-reviewer` |
| `review-changes` | Review uncommitted changes before committing | any | `code-reviewer` |
| `naming` | Check one name against the project's vocabulary | any | — |
| `naming-conventions` | Record the project's naming conventions into `AGENTS.md` | any | — |

The four skills marked *Needs subagent* degrade gracefully — without the agent
they run the review inline and say so — but step 2 is what makes them work as
intended.

### Installing a single skill

```bash
npx skills add valeriinov/flutter_skills --skill naming
```

### Updating

```bash
npx skills update
npx skills list
```

## Subagents

Two Claude Code subagents live in `claude/agents/`:

- **`code-reviewer`** — reviews uncommitted changes for correctness, simplicity,
  consistency with project conventions, architectural fit, duplication, risks,
  and plan compliance when given a plan.
- **`plan-reviewer`** — reviews an implementation plan *before* code is written,
  including an audit of unbacked assumptions.

`/setup-flutter-skills` installs both. To do it by hand instead:

```bash
git clone https://github.com/valeriinov/flutter_skills.git
cp flutter_skills/claude/agents/*.md ~/.claude/agents/
```

Use `<project>/.claude/agents/` instead of `~/.claude/agents/` to scope them to
one project.

## Templates

`templates/AGENTS.project.md` — architecture and naming rules for a single
project. Copy it to your project root as `AGENTS.md` and adapt it. This is the
file the naming skills operate on: `naming-conventions` writes a
`## Naming Conventions` section into it, and `naming` reads that section back
when judging a name. Other skills read it too — `dart-documentation` honors a
`## Documentation` section, and `review-changes` treats `## Review Conventions`
as mandatory context.

`templates/AGENTS.global.md` — cross-project behavioral and style guidelines
(Dart/Flutter style rules, member ordering, documentation style). Install as
`~/.claude/CLAUDE.md` or `~/.agents/AGENTS.md`. Reference material — nothing
installs it automatically.