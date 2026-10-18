---
name: codemap
description: Answer where a Dart symbol is declared and who uses it, from a SQLite index of resolved references; a hook adds it to grep. Use for "где объявлен", "кто использует", "codemap show", "codemap build".
argument-hint: "[ show <Name|Container.name> | build <root> | refresh <root> | map <root> ]"
---

`codemap.py` keeps an index of the Dart symbols of a project in `<root>/.codemap/index.sqlite`.
The index holds each declaration, its signature, its supertypes and each reference with its
source line. `package:analyzer` resolves each reference, so one name in two libraries gives
two symbols. Run `python3 ~/.claude/skills/codemap/codemap.py show <Name>` from a folder of the
project. From another folder, add `--root <root>`.

## When to call it

The hook adds the `show` answer to a grep or `Grep` search for an identifier. Call `show` by
hand in these cases:

- You need a symbol that a search did not name.
- The answer lists more than three declarations. Narrow it with `show <Container.name>`.
- You need the uses of a member, not of its class.

Use grep for literals, regular expressions, comments and text that is not a symbol. A symbol
that the index does not know gives `codemap: no symbol`; then grep the name.

## Commands

| command | result |
|---|---|
| `show <Name>` | declaration `file:line`, signature, supertypes, subtypes, overrides, up to 8 uses with their source line; at most 1000 characters |
| `show <Container.name>` | the same answer for one member |
| `build <root>` | a full index; about 15 s on 2,500 files |
| `refresh <root>` | extracts again the changed files and the files that refer to them |
| `map <root> [--budget 1500]` | the public types and members of the most referenced files |

`show` takes `--root <root>`; without it, the script uses the nearest folder above the current
folder that has `.dart_tool/package_config.json`.

## Index rules

- `build` needs `.dart_tool/package_config.json`. Run `dart pub get` first when it is missing.
- The SDK is `<root>/.fvm/flutter_sdk/bin/cache/dart-sdk` when it exists. If not, the script
  uses the SDK of `dart` on `PATH`.
- The extractor compiles once for each SDK version into `~/.cache/codemap/bin/<version>/`. It
  compiles again after a change of its source.
- `.codemap/` has a `.gitignore` with `*`. Git and ripgrep do not see it.
- The extractor does not parse a file that `analysis_options.yaml` excludes. A reference to its
  symbol gives the file and the line of the declaration.
- After an edit of a `.dart` file, the hook starts `refresh` in the background. Run `refresh`
  by hand only after a change outside the agent tools, for example `git checkout`.

## Hook

`python3 ~/.claude/skills/codemap/codemap.py hook` reads a hook payload on stdin:

- PreToolUse `Bash` or `Grep`: a grep, rg or git grep search gets the answer for up to two
  identifiers, at most 2000 characters. A command that is not a search exits before it reads the disk.
- PostToolUse `Edit`, `Write` or `MultiEdit` of a `.dart` file: a background `refresh`.
- SessionStart and SubagentStart: the map, only when `CODEMAP_MAP=1`.
- `CODEMAP_AB=1`: sessions with an even `session_id` hash get no answer. Each decision goes to
  `<root>/.codemap/ab.log`.
- A missing index starts a background `build`. A project without Dart gets no answer.

## Evals

Run `python3 evals/score.py` from this skill's folder. It compares the extractor output with `evals/fixtures/dart_app/expected.jsonl`.
Then it runs each case in `evals/cases/` on a copy of that fixture.
