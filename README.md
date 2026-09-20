# flutter_skills

Personal AI agent config: skills, subagents, and AGENTS.md conventions.
Flutter-focused, but most of the workflow skills are language-agnostic.

## Install

Two routes. Pick one.

| Route | Installs into | Can replace files you already have |
|---|---|---|
| Claude Code plugin | `~/.claude/plugins/cache/…` | **No.** Skills are `/flutter-skills:<skill>`, agents `flutter-skills:<agent>`. Your own `naming` skill and `flutter-skills:naming` coexist. |
| `npx skills add -g` | `~/.claude/skills/<name>`, plus every other agent directory it detects | **Yes.** A skill of the same name is replaced. |
| Rules files and subagent `.md` files | nothing | Neither route copies them. Placing them by hand can overwrite — see [Rules files](#rules-files). |

### Claude Code (recommended)

Skills and subagents in one step:

```
/plugin marketplace add valeriinov/flutter_skills
/plugin install flutter-skills@flutter-skills
```

Skills appear as `/flutter-skills:<skill>`, agents as
`flutter-skills:code-reviewer` and `flutter-skills:plan-reviewer`. Nothing is
written to `~/.claude/skills/` or `~/.claude/agents/`, so your own skills and
agents keep their names and their content.

Update:

```bash
claude plugin update flutter-skills@flutter-skills
```

Remove:

```bash
claude plugin uninstall flutter-skills@flutter-skills
```

### Other agents (Codex, Cursor, etc.)

Via [npx skills](https://github.com/vercel-labs/skills):

```bash
npx skills add -g valeriinov/flutter_skills
```

Skills only — no subagents. The four review-dispatching skills then run the
review inline and say so.

This route installs by plain name, and the names here are generic — `naming`,
`make-plan`, `commit-changes`. If `~/.claude/skills/naming/` is your own skill,
`-g` replaces it. The installation summary prints an `overwrites:` line before
it acts; with `-y`, or in a non-interactive shell, it proceeds without asking.

Two ways to stay clear of that:

```bash
ls ~/.claude/skills                                   # see what you already have
npx skills add -g valeriinov/flutter_skills -a codex  # install for one agent only
```

Single skill:

```bash
npx skills add -g valeriinov/flutter_skills --skill naming
```

Update:

```bash
npx skills update -g
```

Remove:

```bash
npx skills remove naming -g
```

## Use only some of it

### Plugin

Run `/skills`, highlight an entry, press `Space` to cycle its state: `on` →
`name-only` → `user-invocable-only` → `off`. That writes `skillOverrides` for
you.

By hand, in `~/.claude/settings.json`:

```json
{
  "skillOverrides": {
    "flutter-skills:backend-contract": "off",
    "flutter-skills:naming": "user-invocable-only"
  }
}
```

Plugin entries are namespaced. `"naming": "off"` in that block turns off *your*
`naming` skill; only `"flutter-skills:naming"` touches this one.

### npx skills

Name the skills you want, repeating the flag:

```bash
npx skills add -g valeriinov/flutter_skills --skill naming --skill review-changes
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
| `review-pr` | Review a GitHub PR against its base branch into a document pasted back as comments | any | `code-reviewer` |

## Subagents

Two Claude Code subagents live in `agents/`:

- **`code-reviewer`** — reviews uncommitted changes for correctness, simplicity,
  consistency with project conventions, architectural fit, duplication, risks,
  and plan compliance when given a plan.
- **`plan-reviewer`** — reviews an implementation plan *before* code is written,
  including an audit of unbacked assumptions.

The plugin installs both under the `flutter-skills:` prefix. To do it by hand
instead:

```bash
git clone https://github.com/valeriinov/flutter_skills.git
cp flutter_skills/agents/*.md ~/.claude/agents/
```

That `cp` overwrites `~/.claude/agents/code-reviewer.md` and
`plan-reviewer.md` if you have agents by those names — check first, or rename
the copies. Use `<project>/.claude/agents/` instead of `~/.claude/agents/` to
scope them to one project.

## Rules files

Neither install route copies these. They are yours to place by hand, and each
command below writes over the destination — check what is there first.

### `templates/AGENTS.global.md` — cross-project rules

Behavior, Dart/Flutter style, member ordering.

Additive, if you already keep a `~/.claude/CLAUDE.md`:

```bash
cp templates/AGENTS.global.md ~/.claude/AGENTS.global.md
printf '\n@AGENTS.global.md\n' >> ~/.claude/CLAUDE.md
```

The `@` line imports the file; everything you wrote in `CLAUDE.md` stays where
it is.

With no `~/.claude/CLAUDE.md` of your own, the file can be the whole thing:

```bash
cp templates/AGENTS.global.md ~/.claude/CLAUDE.md
```

For other agents, install it as `~/.agents/AGENTS.md`.

### `templates/AGENTS.project.md` — one project's rules

Architecture and naming rules for a single project. Copy it to your project root
as `AGENTS.md` and adapt it. This is the file the naming skills operate on:
`naming-conventions` writes a `## Naming Conventions` section into it, and
`naming` reads that section back when judging a name. Other skills read it too —
`dart-documentation` honors a `## Documentation` section, and `review-changes`
treats `## Review Conventions` as mandatory context.

## Helper tooling

[`docs/helpers.md`](docs/helpers.md) covers the tooling around the skills: a
token-saving CLI proxy, output-shaping plugins, a statusline, edit-confirm
hooks. Config examples live in [`docs/examples/`](docs/examples/).
