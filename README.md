# flutter_skills

Personal AI agent config: skills, subagents, and AGENTS.md conventions.
Flutter-focused, but most of the workflow skills are language-agnostic.

## Install

### Claude Code (recommended)

Skills and subagents in one step:

```
/plugin marketplace add valeriinov/flutter_skills
/plugin install flutter-skills@flutter-skills
```

Skills appear as `/flutter-skills:<skill>`, agents as
`flutter-skills:code-reviewer` and `flutter-skills:plan-reviewer`.

Update:

```bash
claude plugin update flutter-skills@flutter-skills
```

### Other agents (Codex, Cursor, etc.)

Via [npx skills](https://github.com/vercel-labs/skills):

```bash
npx skills add -g valeriinov/flutter_skills
```

Skills only — no subagents. The four review-dispatching skills then run the
review inline and say so.

Single skill:

```bash
npx skills add -g valeriinov/flutter_skills --skill naming
```

Update:

```bash
npx skills update -g
```

## Skills

| Skill | Purpose | Scope | Needs subagent |
|---|---|---|---|
| `backend-contract` | Write or extend a backend contract from the client implementation and acceptance criteria | any | — |
| `commit-changes` | Split the working tree into logical local commits in a fixed message format; never pushes | any | — |
| `dart-documentation` | Dartdoc for public interfaces and extensions | Dart | — |
| `dart-flutter-tests` | Create, update, or refactor Dart/Flutter tests | Dart/Flutter | — |
| `implement-plan` | Implement a plan file, verify, then review the diff | any | `code-reviewer` |
| `make-plan` | Draft an implementation plan: scout precedent, write, auto-review | any | `plan-reviewer` |
| `naming` | Check one name against the project's vocabulary | any | — |
| `naming-conventions` | Record the project's naming conventions into `AGENTS.md` | any | — |
| `review-changes` | Review uncommitted changes before committing | any | `code-reviewer` |
| `review-plan` | Review a plan file before any code is written | any | `plan-reviewer` |

## Subagents

Two Claude Code subagents live in `agents/`:

- **`code-reviewer`** — reviews uncommitted changes for correctness, simplicity,
  consistency with project conventions, architectural fit, duplication, risks,
  and plan compliance when given a plan.
- **`plan-reviewer`** — reviews an implementation plan *before* code is written,
  including an audit of unbacked assumptions.

The plugin installs both. To do it by hand instead:

```bash
git clone https://github.com/valeriinov/flutter_skills.git
cp flutter_skills/agents/*.md ~/.claude/agents/
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

`templates/AGENTS.global.md` — cross-project rules: behavior, Dart/Flutter
style, member ordering. The plugin does not install it. Either:

- install it as `~/.claude/CLAUDE.md`;
- keep a personal `~/.claude/CLAUDE.md` that starts with `@AGENTS.global.md`
  and copy the file next to it;
- install it as `~/.agents/AGENTS.md` for other agents.

## Helper tooling

[`docs/helpers.md`](docs/helpers.md) covers the tooling around the skills: a
token-saving CLI proxy, output-shaping plugins, a statusline, edit-confirm
hooks. Config examples live in [`docs/examples/`](docs/examples/).
