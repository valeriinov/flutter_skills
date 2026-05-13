---
name: project-init
description: Initialize an existing Flutter project into the GoGoBag-style Clean Architecture baseline. Use when the user explicitly asks to run project-init, initialize a Flutter starter, bootstrap a Flutter app architecture, install project initialization subagents, or create the base app template.
disable-model-invocation: true
argument-hint: "[target-project-path]"
---

# Project Init

Initialize an existing `flutter create` project with a GoGoBag-style Clean
Architecture baseline. This skill is intentionally user-invoked only because it
creates and edits many project files.

Use `$ARGUMENTS` as the target project path when provided. If it is empty, use
the current working directory. Do not run `flutter create`; the target must
already contain `pubspec.yaml` and `lib/`.

## Workflow

1. Resolve the target project root.
2. Run `scripts/install_subagents.dart` from this skill to copy project-scoped
   subagents into the target:
   - Claude Code: `.claude/agents/project-init-*.md`
   - Codex: `.codex/agents/project-init-*.toml`
3. If the active CLI cannot see the new custom agents yet, tell the user to
   restart the Claude/Codex session and re-run this skill. Custom subagents are
   usually loaded at session startup.
4. Run `scripts/collect_config.dart` to collect the initialization config.
   Keep the generated config JSON and pass it to every worker.
5. Run the implementation agents in this order:
   - `project-init-dependencies` first.
   - `project-init-foundation`, `project-init-state`,
     `project-init-data-network`, `project-init-theme-localization`, and
     `project-init-app-shell` in parallel when the environment supports
     parallel subagents.
   - `project-init-docs`.
   - `project-init-verifier`.
6. If custom agents are not available in the active CLI, use built-in worker
   subagents with the matching prompt from `assets/agents/claude/`.

## Config Defaults

When the user does not choose differently, use:

- state management: `cubit`
- languages: `en`
- flavors: `standard` (`dev`, `for_test`, `preprod`, `prod`)
- Dio network layer: enabled
- splash setup: enabled
- launcher icons setup: enabled
- initial feature: `home`

Local database setup is intentionally out of scope for this skill. Do not prompt
for it and do not mention it in generated project docs.

## Dependency Policy

Use `references/dependency_catalog.yaml` as the only source of dependency
constraints. Do not install blind latest versions.

After generation:

1. Run `pub get` using the project command style (`fvm flutter pub get` when the
   target project uses FVM, otherwise `flutter pub get`).
2. Run `pub outdated --json`.
3. Run `scripts/audit_dependencies.dart` with the outdated JSON and the catalog.
4. Report compatible updates and breaking-major candidates to the user.

Do not update constraints based on the audit report. Dependency catalog upgrades
belong to a future separate skill.

## Flavor And Asset Rules

For multi-flavor projects, generate `flavorizr.yaml` with placeholders for app
names, Android application IDs, and iOS bundle IDs. Do not run
`flutter_flavorizr`; tell the user to fill the placeholders and run it manually.

When splash setup is enabled, generate `flutter_native_splash.yaml` for
single-flavor projects or one `flutter_native_splash-<flavor>.yaml` file per
flavor.

When launcher icons setup is enabled, generate `flutter_launcher_icons.yaml` for
single-flavor projects or one `flutter_launcher_icons-<flavor>.yaml` file per
flavor.

## Verification

Before finishing, run the strongest practical checks for the target project:

```bash
fvm dart run build_runner build --delete-conflicting-outputs
fvm dart format .
fvm flutter analyze
```

If FVM is unavailable, use the same commands without the `fvm` prefix. Report
any command that could not be run.
