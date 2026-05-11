# AGENTS.md

Global behavioral and style guidelines for AI agents.
Merge with project-specific instructions as needed.

## Universal Behavioral Guidelines

### 1. Think Before Coding

**Don't assume. Don't hide confusion. Surface tradeoffs.**

Before implementing:
- State your assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them — don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.

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

Strong success criteria let you loop independently. Weak criteria ("make it work") require constant clarification.

## Language-Specific Style Rules (Dart / Flutter)

### General Principles

- Code must be easily readable and follow the principles of *Clean Code* by Robert C. Martin.
- Avoid nested structures (loops or conditionals). The structure should remain flat:
    - use early returns (guard clauses);
    - split logic into small private methods.
- Extract conditions into predicate methods when it improves clarity:
    - do not extract trivial branches if their meaning is already obvious at the point of use.
- Method bodies must always use curly braces; never use `() => ...`.
- Method and variable names must be clear, consistent, and stylistically unified. Avoid names that are excessively short or long.
- Do not explicitly declare the variable type on the left side of `=` if the type is already defined or obvious on the right side.
- After every code change: run formatting and static analysis with zero errors.
  - With FVM (`.fvmrc` or `.fvm/` exists):
    - `fvm dart format .`
    - `fvm flutter analyze`
  - Without FVM:
    - `dart format .`
    - `flutter analyze`
  - Fix **all** errors and warnings before finishing. Zero tolerance for analysis issues.

### Member Ordering

#### General Types (classes, mixins, enums, extensions)

**Order:**

1. Static fields
2. Public fields (non-nullable)
3. Public nullable fields
4. Private fields (non-nullable)
5. Private nullable fields
6. Constructors
7. Named constructors
8. Factory constructors
9. Public getters
10. Public setters
11. Private getters
12. Private setters
13. Overridden public methods (e.g., `@override` from interfaces/superclasses)
14. Public methods
15. Private methods

#### Flutter Widgets (StatelessWidget / StatefulWidget / State)

**Order:**

1. Static fields
2. Public fields (non-nullable)
3. Public nullable fields
4. Private fields (non-nullable)
5. Private nullable fields
6. Constructors
7. Named constructors
8. Factory constructors
9. Public getters
10. Public setters
11. Private getters
12. Private setters
13. initState (State only)
14. didChangeDependencies (State only)
15. didUpdateWidget (State only)
16. build
17. Public methods
18. Private methods
19. dispose (State only)

**Notes:**

- `build` is the anchor; lifecycle methods stay **above** it and `dispose` stays **below** it.
- Do not move UI into private methods like `_buildHeader()` / `_buildTile()`.
    - If a UI section is large, extract it into a separate widget file.
    - If a UI section is small and local, use a private widget class in the same file (for example: `_EmailField`, `_SubmitButton`).

**Private method ordering**

- Private methods must be ordered according to the effective first usage in the file.
- If a private method is used in multiple places, its latest usage determines its placement (i.e., treat the last call site as the "first" for ordering).
- The goal is for the reader to encounter call sites first, and then see implementations below, maintaining a top-down reading flow.

### Documentation Style (Dart)

**Scope**

- Document **only** public **interfaces** (`abstract interface class …`) and **extensions**.
- Skip docs for private members and trivial/public API where meaning is obvious.

**Format**

- Use Dartdoc `///` comments.
- Language: **English**.
- Optional category tag at the top: `/// {@category <Name>}`.
- Order inside a block:

    1. **One-sentence summary** (what it is).
    2. **Details** (optional; when it helps understanding).
    3. **Parameters** using the exact phrasing:
       `The [parameterName] parameter is ...`
    4. **Returns** (if non-void): concise sentence.
    5. **Throws** (optional).
    6. **Example:** code block labeled with `Example:`.

**Style**

- Be concise; avoid redundancy with names/types.
- Prefer present tense ("Returns…", "Provides…").
- Keep lines short and readable.
- Don't restate obvious types or names.
- Use meaningful examples; keep them minimal and runnable.

**Do / Don't**

- **Do:** document interface contracts and extension behavior.
- **Do:** explain side effects, preconditions, postconditions.
- **Don't:** document private helpers or self-evident getters/setters.
- **Don't:** duplicate information already clear from names or types.
