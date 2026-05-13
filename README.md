# flutter_skills

Flutter development skills for AI agents.

## Installation

Install skills from this repository into your project using [
`npx skills`](https://github.com/vercel-labs/skills):

```bash
# Install all skills
npx skills add valeriinov/flutter_skills

# Install into a specific agent (e.g., Claude Code)
npx skills add valeriinov/flutter_skills --agent claude-code

# Install a specific skill
npx skills add valeriinov/flutter_skills --skill document-code
```

### Update

```bash
npx skills update
```

### List installed skills

```bash
npx skills list
```

## Skills

### project-init

`project-init` initializes an existing Flutter project into a GoGoBag-style
Clean Architecture baseline. It is an explicit skill: invoke it directly when
you want to mutate a target project.

Install the skill as usual, then run it from the target Flutter project:

```bash
$project-init
```

Or pass a target project path:

```bash
$project-init /path/to/flutter_project
```

The target must already be a Flutter project with `pubspec.yaml` and `lib/`.
The skill does not run `flutter create`.

#### What It Configures

The v1 initializer asks for:

- state management: Cubit or Riverpod
- supported languages
- flavor setup: none, standard, or custom flavors
- whether to include Dio
- whether to include splash configuration
- whether to include launcher icon configuration
- the initial feature name

The fixed stack includes `dartz`, `get_it`, `injectable`, `auto_route`,
`easy_localization`, `theme_tailor`, `flutter_dotenv`, `flutter_hooks`,
`freezed`, `json_serializable`, `build_runner`, and `flutter_gen_runner`.

#### Project-Scoped Subagents

On first run, `project-init` installs subagent templates into the target
project:

```text
.claude/agents/project-init-*.md
.codex/agents/project-init-*.toml
```

These files are project-scoped and can be checked into the target repository.
If Claude Code or Codex does not see them immediately, restart the CLI session
and invoke `project-init` again.

#### Dependencies

The skill uses tested caret constraints from
`skills/project-init/references/dependency_catalog.yaml`. It does not install
blind latest package versions.

After generation, the skill runs `pub outdated --json` when possible and
reports:

- compatible updates that may be safe within the tested major line
- newer major versions that need separate validation

It does not update dependency constraints from the audit report.

#### Flavors, Splash, And Icons

For multi-flavor projects, the skill generates `flavorizr.yaml` with
placeholders for app names, Android application IDs, and iOS bundle IDs. It
does not run `flutter_flavorizr` automatically. Fill the placeholders first,
then run the generated flavor command.

When selected, the skill also creates `flutter_native_splash` and
`flutter_launcher_icons` config files. In multi-flavor projects these are
generated per flavor.
