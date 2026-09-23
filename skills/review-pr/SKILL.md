---
name: review-pr
description: 'Review a GitHub PR against its base branch into a document the user pastes back as comments; later rounds append verdicts. Use for "сделай ревью PR #N", "сверь правки по PR", "review PR #N".'
argument-hint: "[ PR number, optionally: focus or concern ]"
---

Review the pull request the user names; ask for the number if none is given. A focus or
concern named along with it narrows the review.

The deliverable is a document the user pastes into GitHub as comments — not a chat
answer. `review-changes` is the wrong tool here: it reads the working tree, and a PR
lives in a branch.

## 1. Resolve the target

```bash
gh pr view <N> --json number,title,body,headRefName,baseRefName,additions,deletions,changedFiles
git fetch origin <headRefName> <baseRefName>
git worktree add --detach .worktrees/pr-<N>-review origin/<headRefName>
```

Always the worktree, and read every file from there: each finding carries `path:line`, and
those numbers must be the PR HEAD's own. Keep it until the user says the review is over,
then `git worktree remove`. Record the HEAD sha — the document's header states it, together
with the base sha.

Diff against the fetched remote base, never a local branch of the same name: a local base
that has fallen behind pulls a merged neighbour's commits into the diff, and they read as
this branch's own work. `git merge-base <base> <head>` must equal the head of `<base>`;
when it does not, fetch and recompute before reading a single line.

## 2. Scope the diff

Three-dot diff, generated files excluded:

```bash
git diff origin/<base>...origin/<head> -- . ':(exclude)*.freezed.dart' ':(exclude)*.g.dart' ':(exclude)*.config.dart'
```

Take the project's own generated markers from its AGENTS.md / CLAUDE.md when it names them
(codegen output, locale keys, DI config, lockfiles, vendored trees); the list above is the
Dart/Flutter default. `git diff --stat` over the same exclusions gives the file count for
step 3.

When the branch is one of a stack (rule 6 of step 6), each request is scoped to its own
base: the first against the trunk, the one stacked on it against the first request's head —
`<first-head>...<stacked-head>`, never `<trunk>...<stacked-head>`, which would hand the
second request everything the first already carries.

## 3. Pick the depth

- ≤ 25 non-generated files — one `code-reviewer` agent over the branch diff.
- Over 25 — one agent per layer of the project's actual tree (domain / data / presentation /
  tests, or whatever the repo really has), then deduplicate their findings yourself.

Every agent prompt states: the changes are **not** uncommitted, review
`git diff origin/<base>...origin/<head>`; read full files from the worktree at
`.worktrees/pr-<N>-review`; report line numbers as they are there; ignore generated files.
Carry the same emphasis `review-changes` uses — naming against the project's real
vocabulary with cited precedent, consistency of approach, what can be simplified, theme
values from the theme extensions — and the restraint rules of the project's
"Review Conventions" (or the document that section points to).

## 4. Verify before writing anything down

Re-check each finding against the file in the worktree yourself. Drop the ones that do not
hold and say in one line which and why. A reviewer agent always returns "Needs revision" —
that verdict is not evidence.

## 5. Write the document

Path: `plan/pr_reviews/PR-<N>-<TICKET>-<slug>.md` when the repo has a `plan/` directory;
otherwise ask where it goes.

Ukrainian, plain words, copy-paste-ready as a GitHub comment. No tables. No summary of the
diff, no restating what the author wrote, no filler. Header, then numbered items:

```markdown
# Ревʼю PR #42 — APP-17

Перевірено на `3f9a1c2b7` (база `9b1e04c62`).

**Знайдено 24.** 🔴 2 · 🟡 7 · 🟢 15

🔴 блокує злиття · 🟡 суттєве · 🟢 дрібне

---

## 9. 🟡 Групування тисяч застосоване лише в новому коді

`lib/presentation/ui/widgets/cart_shared/cart_discount_title.dart:65-66`
`lib/presentation/ui/widgets/cart_shared/common_cart_additional_info.dart:152-155`

**Проблема.** `AppNumberFormats` викликається тільки з двох нових віджетів. Той самий
факт в інших місцях і далі малюється голим `.toString()`:
`support_chat_message_list_view.dart:154-155`, `common_price_info.dart:143, 145`.

**Пропоную.** Або провести ці місця через `AppNumberFormats.amountFormat` у цьому ж PR,
або прибрати групування з нових віджетів і завести окремим тікетом.
```

🔴 blocks the merge · 🟡 significant · 🟢 minor — the header carries that scale as its own
Ukrainian line under the tally, so a reader of the pasted comment knows what the balls
mean. `**Пропоную.**`, never `**Треба.**`. A side question the user asked along the way is
answered in chat in Russian — it never goes into the document.

An item that asks for **new coverage** rather than for a broken or stale test is the
author's call and is never forced: it carries a `**На розсуд автора.**` paragraph naming
the reason — under `**Пропоную.**` when the item is written with the marking, under the
round block that classified it otherwise. A test that cannot fail, duplicates its
neighbour or documents behaviour the code no longer has is a defect like any other and is
never marked. The marking then rides the closing section and the header tally of step 6.

## 6. Later rounds — append only

When the author has pushed fixes: `git fetch`, move the worktree to the new HEAD, then walk
the existing document.

Each item gets one new block inserted under its body — one targeted insert per item:

```markdown
**Раунд 2 (`7c9d910b1`).** ✅ Зроблено — конверт прибрано, поле всюди `discountAmount`
(`discount_preview_response_dto.dart:14-22`, `cart_data_dto.dart:26`).
```

Statuses: ✅ Зроблено · ⚠️ Частково · ❌ Не зроблено. An item the user decides not to
pursue gets a `**Знято.**` paragraph under its round block carrying the reason, and leaves
the open lists. Evidence carries the line numbers of the new HEAD.

Rules for the round, in order of importance:

1. The heading and the body an earlier round wrote stay byte-for-byte. Never rewrite the
   file whole — no overwrite, no `cat > … <<'MD'`. Only inserts. `git diff` of the
   document must show additions and no deleted lines inside item bodies. `plan/` is often
   gitignored, so copy the document to a scratch file before the first insert and prove it
   afterwards: `diff <scratch> <doc> | grep '^<'` returns nothing but lines of the header
   block and of the closing section of rule 5.
2. New findings go to the bottom, under `# Нові зауваження`, numbering continuing from the
   last item — above the closing section of rule 5. One heading holds the findings of
   every round, so each item opens with the round that raised it, above `**Проблема.**`:

   ```markdown
   **Новий у раунді 3 (`7c9d910b1`).** Породжений правкою пункту 1: …
   ```

   The cause clause is there when the round's own fixes produced the defect — the file the
   item names is in that round's diff, and the author reads it as fallout from the commit
   they just pushed rather than as one more thing noticed late. A finding in a file the
   round did not touch carries the round line alone.
3. Only the header block is rewritten, and it keeps one paragraph per round: the round
   line (number, HEAD, base) and that round's lint line. Under them stands the tally the
   round replaces: `**Закрито 17 із 24.** Відкриті: 2 (частково), 3, 6. Знято: 7.
   Новий: 25. На розсуд автора — 9, 20.`
4. Name the stop condition before starting a series of rounds, and read the **calibre** of
   what comes back, not the count: once findings move from "defect in the app" to "defect
   in a document or in the harness", stop and hand the rest to the user as a list.
5. The document ends with a closing section that every round rewrites whole — the only
   part besides the header that is not append-only. It is the check-list the author works
   from, so it repeats the current state of each open item instead of pointing back at it.

   One block per item that is not ✅ and not **Знято**, ordered by number, each carrying
   `path:line` of the current HEAD and what to do. One marker follows the number: the
   item's round verdict when it has one, its severity ball when no round has given it a
   verdict yet.

   ```markdown
   ---

   # Що лишилось поправити

   **7 ⚠️** — `<path:line>`: <що зараз не так>. <що зробити>.

   **20 ❌ (на розсуд)** — `<path:line>`: <…>

   **25 🟢** — `<path:line>`: <…>
   ```

   An item carrying the `**На розсуд автора.**` paragraph of step 5 takes `(на розсуд)`
   after its marker here, and is listed under `На розсуд автора — …` in the header tally
   without a marker of its own. Close the section with a one-line note
   for each item the user withdrew, so a reader does not go looking for it.
6. A branch may reach review as a stack of requests rather than one. Whether it does, and
   where the seam runs, is the project's own convention — its git-workflow document, its
   `AGENTS.md`/`CLAUDE.md`, or the request descriptions themselves; never assume a split
   the project has not written down. When there is one, the closing section of rule 5 gets
   one `##` per request, in merge order, each headed by the request's number and branch,
   and every item goes under the request whose diff carries the file it names:

   ```markdown
   ## <Роль першого реквесту> #<N> (`<head>` → `<base>`)

   **7 ⚠️** — …

   ## <Роль другого реквесту> (`<head-of-the-stacked-branch>`)

   **20 ❌ (на розсуд)** — …
   ```

   An item whose halves fall on different requests appears under both, marked
   `(половина)` / `(друга половина)`. An item the earlier request cannot close on its own
   — a key whose only reader the other request deletes, a document the other request
   rewrites — is **Знято** with the reason, because the trunk ends up consistent once both
   land; say in one line that the intermediate state lives only between the two merges.
   A single-request branch gets one flat list and no subheadings, and a stack falls back
   to that flat list as its requests merge: a merged request leaves the section once its
   own open items are closed or **Знято** with the merge named, and the request left
   standing loses its heading.

## 7. Rules

- Never post to GitHub, never push, never commit. The user pastes the comments themselves.
- Never change the reviewed code — that is a separate request, after the user confirms.
- The branch lint gate (`analyze` / metrics / bloc lint / format check, via the project's
  own lint skill, run inside the worktree) is for a later round or an explicit ask, and its
  result is one line in the header. A fresh worktree may need the project's dependency
  fetch and analyzer-plugin bootstrap first, otherwise it answers a false green.
- Chat stays Russian and short: the verdict, what was dropped in step 4, and the path to
  the document.
