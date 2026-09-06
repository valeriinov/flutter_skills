# Helpers

Optional tooling the author runs next to the `flutter-skills` plugin. Nothing
here is required by the skills; every section stands on its own.

Paths below are relative to a checkout of this repo:

```bash
git clone https://github.com/valeriinov/flutter_skills.git && cd flutter_skills
```

Snapshots referenced below live in `docs/examples/`:

- `docs/examples/settings.json` — only the `hooks`, `enabledPlugins`,
  `extraKnownMarketplaces` and `skillOverrides` keys. It is not a complete
  settings file: **merge** these keys into your own `~/.claude/settings.json`.
  It also registers the `anthropics/skills` marketplace, unrelated to the
  plugins below — keep or drop it.
- `docs/examples/CLAUDE.md` — the author's personal `~/.claude/CLAUDE.md`, verbatim.

## Plugins (Claude Code)

Install pattern, per plugin:

```
/plugin marketplace add <owner/repo>
/plugin install <name>@<name>
```

### claude-hud — `jarrodwatts/claude-hud`

Statusline HUD.

```
/plugin marketplace add jarrodwatts/claude-hud
/plugin install claude-hud@claude-hud
/claude-hud:setup
```

Run `/claude-hud:setup` after install. Do not copy a `statusLine` block from
someone else's settings — it carries machine-specific paths.

### caveman — `JuliusBrussee/caveman`

Compressed output modes plus the `cavecrew-*` subagents (investigator, builder,
reviewer) whose output is caveman-compressed.

```
/plugin marketplace add JuliusBrussee/caveman
/plugin install caveman@caveman
```

The settings example sets `"skillOverrides": {"caveman-commit": "off"}` because
the `commit-changes` skill owns the commit format.

### i-have-adhd — `ayghri/i-have-adhd`

Action-first output shaping.

```
/plugin marketplace add ayghri/i-have-adhd
/plugin install i-have-adhd@i-have-adhd
touch ~/.claude/.i-have-adhd-always   # always-on
```

The `UserPromptSubmit` echo hook in the settings example is the author's own
reminder line, in Russian. Optional — edit the text or drop the hook.

## RTK — token-saving CLI proxy

Rewrites shell commands (`git status` → `rtk git status`) and trims their output.

```bash
brew install rtk
rtk --version   # rtk X.Y.Z
rtk gain        # must work; if not, a different "rtk" binary may be on PATH
```

The `PreToolUse` hook on `Bash` in the settings example — `rtk hook claude` —
does the rewriting. Install rtk before merging that entry, or drop the entry.

Give the agent the meta commands:

```bash
cp docs/examples/RTK.md ~/.claude/RTK.md
echo '@RTK.md' >> ~/.claude/CLAUDE.md
```

## Edit-confirm hooks

Two scripts that make each session choose, once, between confirming every edit
and full auto. They need `jq` on `PATH`.

```bash
mkdir -p ~/.claude/hooks
cp docs/examples/hooks/*.sh ~/.claude/hooks/
```

Wired by the two `$HOME/.claude/hooks/...` entries in the settings example:

- `SessionStart` → `edit-confirm-session-start.sh` injects an instruction:
  before the first edit, ask the user "Confirm every edit" vs "Full auto" and
  write the single word `confirm` or `auto` into
  `/tmp/claude-edit-confirm/mode-<session_id>`.
- `PreToolUse` on `Edit|Write|MultiEdit|NotebookEdit` → `edit-confirm-pre.sh`
  reads that file: `allow` for `auto`, `ask` otherwise (missing file = confirm).

Approving one edit prompt never flips the session to auto; only an explicit
chat request does.

## Personal CLAUDE.md via `@` imports

Recipe for `~/.claude/CLAUDE.md`:

```markdown
# CLAUDE.md

@AGENTS.global.md

## Personal additions
...

@RTK.md
```

```bash
cp templates/AGENTS.global.md ~/.claude/AGENTS.global.md   # next to CLAUDE.md
```

`docs/examples/CLAUDE.md` is the author's file as-is. Before reusing it:

- "Review Routing" and "Skills and agents" name personal skills — `review-pr`,
  `weekly-retro`, `add-openrouter-picker-model`, `export-flutter-skills` — and the
  caveman commands
  (`caveman-review`, `cavecrew-reviewer`). Drop those lines unless you have the
  same skills and plugins.
- "Output Shape" presumes the `i-have-adhd` plugin and `cavecrew-*` subagents.
