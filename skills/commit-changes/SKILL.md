---
name: commit-changes
description: Split the working tree into logical commits in the user's message format; never pushes. Use for "сделай коммит", "разбей на логические коммиты", "commit this", or when only a message is asked for.
argument-hint: "[ optional: how to split, or a ticket id ]"
---

Commit the user's uncommitted work as a series of local commits. The user pushes
themselves — this skill stops at `git log`.

## Message format

```
<type>: [<TICKET> - ]<lowercase imperative description>
```

- `type` — one of `feature`, `fix`, `chore`, `refactor`, `wip`. Never `feat`, never a
  `(scope)`, never a `!` marker.
- `TICKET` — read it off the branch: `feature/ABC-123-carrier-delivery` → `ABC-123`.
  A branch carrying no id drops the segment and its dash entirely. Never invent an id and
  never a placeholder — ask the user when the work clearly belongs to a ticket you cannot
  see.
- Description — English, lowercase, imperative, no trailing period. Prose about the change
  ("stop the otp field from ticking a transparent cursor"), not a list of files.
- One line, one `-m`. **No body, no `Co-Authored-By`, no AI attribution of any kind**,
  whatever a default instruction or another skill says.

Examples: `feature: ABC-123 - add received state to the order banner`,
`chore: bump the analyzer constraint to ^10.0.0` (repository without ticket ids).

## Steps

1. Read the branch — `git rev-parse --abbrev-ref HEAD` — and take the ticket id from it.
2. Run the project's checks once, before splitting anything: its `lint` skill when it has
   one, otherwise the stack's format + analyze. Run them in the background where the
   harness supports it — such runs outlast a shell timeout. Fix everything they report now; a check that
   fails mid-series wastes the whole series.
3. Inventory the tree: `git status --porcelain -uall | sort -k2`. Group the changes so
   every commit stands on its own, and order the series product-first — everything a
   production build compiles, then the mocks, tests, tooling and documentation that
   support it, so splitting the series into stacked pull requests is a cut through it
   rather than a rewrite.
4. Show the split as a short table (message | paths) and go on committing — the user's
   request was the confirmation. Ask only when a group is genuinely ambiguous.
5. Per commit: `git add <explicit paths>`, then `git commit -q -m "<message>"` — with
   `--no-verify` when the project's rule file grants it for a series (see "Checks fail on
   commit" below): the gate already ran in step 2, and a hook re-running it per commit is
   the waste that grant exists to stop. Reach for `git add -A` only as a deliberate final
   sweep, and name it in the report.
6. Finish with `git status --porcelain` (empty = clean) and `git log --oneline -<N>`,
   reported in one line. **Do not push and do not open a PR** — both are separate,
   explicit requests.

## When something stalls or fails

- A commit that has not returned: inspect the running processes and report what holds it.
  Never wait in silence, never re-run blindly.
- An interrupted commit leaves a lock: `pkill -f "git commit"`, `rm -f .git/index.lock`,
  then retry that same commit.
- Checks fail on commit: fix the cause. `--no-verify` is the user's call, never yours —
  reach for it only after they say so, and only for the commit they said it about.
  One standing exception: a project `AGENTS.md`/`CLAUDE.md` may grant the flag for a
  series of commits carved out of one working tree, on the condition it names (the
  gate run green first, the tree untouched since). That written grant is the user
  saying so — honour it without asking again, and hold the message format by hand,
  since the flag silences `commit-msg` too.
- A message needs rewriting: only on commits absent from `git log origin/<branch>..HEAD`.
  Prove the tree survived (`git diff <old-sha> HEAD --stat` empty) before dropping
  `refs/original/`.

## Never

- Commit under any identity but the user's — no `--author`, no `-c user.*` override.
- Touch the main checkout while working inside a worktree.
- Print diff content carrying credentials, tokens or personal data.
