# Global rules

Behavioral and style guidelines for AI agents, shared across projects.

## Universal Behavioral Guidelines

### 1. Think Before Coding

**Don't assume. Don't hide confusion. Surface tradeoffs.**

Before implementing:

- State your assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them — don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.
- A question is answered, not executed: "can we do without X?" gets what X gives
  and what dropping it costs; the code, the plan and the document stay as they
  were until the user says to change them.
- Never assert a fact you haven't read or checked — about the codebase, the
  running app, the device, the git state or an agreement — in dialogue, a report,
  a contract or a diagram alike. Cite `file:line` or the command output, or say
  the claim is unverified; a proposal is written as a proposal, never as settled.

### 2. Simplicity First

**Minimum code that solves the problem. Nothing speculative.**

- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- No error handling for impossible scenarios.
- If you write 200 lines and it could be 50, rewrite it.

Ask yourself: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

### 3. Surgical Changes

**Touch only what you must. Clean up only your own mess.**

When editing existing code:

- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code, mention it — don't delete it.

When your changes create orphans:

- Remove imports/variables/functions that YOUR changes made unused.
- Don't remove pre-existing dead code unless asked.

The test: Every changed line should trace directly to the user's request.

### Git and Worktree Transfers

- When moving changes between worktrees or branches, do not commit them without
  the user's explicit request.

### 4. Goal-Driven Execution

**Define success criteria. Loop until verified.**

Transform tasks into verifiable goals:

- "Add validation" → "Write tests for invalid inputs, then make them pass"
- "Fix the bug" → "Write a test that reproduces it, then make it pass"
- "Refactor X" → "Ensure tests pass before and after"

For multi-step tasks, state a brief plan:

```
1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]
```

Strong success criteria let you loop independently. Weak criteria ("make it work") require constant
clarification.

A loop that repeats a round — review → fix → re-review, generate → judge → regenerate —
names its exit condition before the first round runs, and the condition is something
other than a reviewer's approval. A review agent returns "needs revision" by
construction, so "loop until it approves" has no floor. Name a round cap, a
severity floor, or a green command, and stop there even if findings remain.

A check reported as passed names the command or measurement it ran and the threshold it
was held to — analyze, tests, a device capture. A number outside the threshold the
user set is not "ok", whatever verdict the tool prints; say which gate ran before saying
done.

A workflow or fan-out spawns at most five agents per run, counted along the run's longest
path — sweep, lenses, verifiers, fixer and gate together. Over five, collapse the fan
(one lens instead of three, one sceptic over the list instead of one per candidate, a
pipeline instead of a fan-out); never raise the cap.

### 5. Communication

- Always respond in Russian. Code, identifiers, commit messages, and Dartdoc stay
  in English.
- Never use "сиблинг" in dialogue, nor "sibling"/"siblings" in code, comments,
  Dartdoc, markdown or commit messages (any project). Russian: "соседний
  файл/класс", "рядом лежащий", "однотипный", "аналогичный". English: name the
  relation itself — "the neighbouring file/class", "the other five statuses",
  "both root-level routes", "everything else in this folder".

### Output Shape

The reader has ADHD. Shape every prose the user reads — dialogue, plans, reports:

- Lead with the action: command, path, or snippet first. No preamble, no recap, no closers.
- Number multi-step work, one bounded action per step.
- Cap lists at 5 items; end with one next action under two minutes.
- Errors: state location, cause, and fix. No drama.
- Exceptions: confirm destructive actions; after three failed fixes name the doubtful assumption;
  ask one short question when the request is ambiguous.
- Plan file: Context ≤3 lines, one step = `action → verify: check`, files as a `path | change`
  table, ~40 lines max. No codebase retelling, no rejected alternatives, no prose replay of the
  plan in chat.
- A harness mandate fixes which sections exist, not how long they are. Full length only when asked
  to explain — a follow-up question is not that ask. No time estimates at all unless asked outright.
  Progress restated in one clause, never duplicating a task checklist.
- Verify a subagent's findings, then relay what survives in its own form — never retell it as prose.
- A run that goes quiet is a run the user interrupts. Before a stretch that will hold the
  turn — a delegated fan-out, a long device or lint loop — say in one line what is running
  and what will end it; while it runs, surface each round's result as it lands rather than
  banking them for a final report. "Still working" is not a signal; the round number and
  what it found is.

Precedence when it collides with the rules above:

- It sets form, not language: replies stay Russian (§5).
- §1 assumptions go after the first action line — two lines max, or one clarifying question.
- Code, commit messages, and Dartdoc stay normal prose.

### Review Routing

- "Сделай ревью" / "проанализируй изменения" / "review the diff" defaults to
  the `review-changes` skill (deep review via the code-reviewer agent).
- Built-in `/code-review` — only when named explicitly.
- Tests: creating, updating or refactoring anything under `test/` goes through
  the `dart-flutter-tests` skill — never ad hoc test files.
- Name checks ("удачное ли имя", "консистентность нейминга", "чисто и консистентно с
  проектом" / "разве не консистентней" said of a name) → `naming` skill; the same words
  said of an approach or a pattern → `review-changes`.
- "Имплементируй план" → `implement-plan` skill; "сделай ревью плана" / "проанализируй
  план" → `review-plan` skill — also when the request adds "используй субагентов".

### Skills and agents

- A skill or agent body describes the mechanism, not the instance: no ticket id, project
  name, device model or harness feature that another machine or agent will not have.
  Examples come from the skill's own domain; a project-bound example belongs in that
  project's own skill.

### 6. Naming

- A name must state what the code actually does — nothing more.
- Ground proposed names in existing project vocabulary (grep the neighbouring
  names first, then name).

### 7. Documentation

**A document states what is true now, never what changed.**

- No "used to", "no longer", "previously", no rationale framed as a diff from an
  earlier version. Superseded text is deleted, not kept as contrast.
- Every surface: markdown, Dartdoc, comments. History lives in git and the PR.
- Exception: a migration or compatibility note the reader must act on, if asked.

### 8. Comments

**Say it in code; comment only what code cannot say.**

- First rename, extract a predicate or method, or name the constant.
- Allowed: SDK or framework behaviour, an external contract, an ordering whose
  breach fails silently — one sentence naming the mechanism, never domain "why".
  Doc comments on private members and tests meet this bar too — a rare case.
- Never: restating adjacent code, one fact twice. Existing comments are no
  precedent.
- Before done, check every added comment line, new files included.


## Language-Specific Style Rules (Dart / Flutter)

### General Principles

- Prefer obvious, boring code over clever code.
- Avoid nested structures (loops or conditionals). The structure must remain flat:
    - use early returns (guard clauses) — always with curly braces: `if (condition) { return; }`;
    - never nest more than one level deep inside any block — extract deeper logic
      into a private method.
- Extract logic into private methods and conditions into predicate methods to
  keep code readable.
    - When a condition contains more than one `&&`/`||` operator, always extract
      it into a named private predicate method.
- Use arrow syntax only for single-expression bodies where meaning is obvious. Prefer curly braces
  for multi-line or conditional logic.
- Method and variable names must be clear, consistent, and stylistically unified. Avoid names that
  are excessively short or long.
- Never use `var`. Prefer `final` for immutable bindings. For mutable variables, declare the type
  explicitly: `int index = 0`.
- Do not explicitly declare the variable type on the left side of `=` if the type is already defined
  or obvious on the right side.
- Never use the `!` null assertion operator. Instead, handle nullability explicitly.
- After every code change: run formatting and static analysis with zero errors.
    - Run `fvm dart format . && fvm dart analyze` (or without `fvm` prefix if not used)

### Member Ordering

General types (classes, mixins, enums, extensions):

Static fields → public fields (non-nullable) → public nullable fields → private fields
(non-nullable) → private nullable fields → constructors → named constructors → factory
constructors → public getters → public setters → private getters → private setters →
overridden public methods (`@override` from interfaces/superclasses) → public methods →
private methods.

Flutter widgets (StatelessWidget / StatefulWidget / State) share those first twelve
positions, then diverge: `initState` → `didChangeDependencies` → `didUpdateWidget` →
`build` → public methods → private methods → `dispose` (lifecycle members State-only).
Widgets have no overridden-public-methods slot. `build` is the anchor: lifecycle methods
stay **above** it and `dispose` stays **below** everything else.

**Notes:**

- Do not move UI into private methods like `_buildHeader()` / `_buildTile()`.
    - If a UI section is large, extract it into a separate widget file.
    - If a UI section is small and local, use a private widget class in the same file (for example:
      `_EmailField`, `_SubmitButton`).

**Private method ordering**

- Private methods must be ordered according to the effective first usage in the file.
- If a private method is used in multiple places, its latest usage determines its placement (i.e.,
  treat the last call site as the "first" for ordering).
- The goal is for the reader to encounter call sites first, and then see implementations below,
  maintaining a top-down reading flow.

### Documentation Style (Dart)

Scope, format, style rules and templates live in the `dart-documentation` skill — load it
when writing or reviewing Dartdoc. A project `AGENTS.md` may extend the scope, the
`{@category}` whitelist and the line limit; those additions win.

