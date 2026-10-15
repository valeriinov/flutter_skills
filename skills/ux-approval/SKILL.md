---
name: ux-approval
description: Run UI text approval rounds in a shared artifact: create, next round from answers and the project, finalize. Use for "утверди тексты", "следующий раунд", "approval round".
argument-hint: "[ ux-translate brief, review and locale files | artifact url + next round | artifact url + finalize ]"
---

Run from the project whose branch will receive the approved texts. The artifact is the source of
truth until the export: each round keeps its brief, a snapshot of every key, the review and the
answers. You publish the artifact and read its database yourself. The project is only read —
for the reconcile and for key context; its files are never written. Working files go to the
session's scratch directory, written below as `<scratch>`. `approval.py` runs from this skill's
folder; `check_drafts.py` is the neighbouring skill's, `../ux-translate/check_drafts.py`.

## Mode

| request | mode |
|---|---|
| no artifact yet: ux-translate outputs and locale files named | Create |
| artifact url, its latest round closed by the owner | Next round |
| artifact url + "финализируй" / "finalize" | Finalize |

Latest round still open (no `rounds/<n>` document) → tell the user the owner closes it with
"Завершити раунд" on the page, and stop.

## Spec shape

You write the spec; `approval.py check` validates it and `build` turns it into the page.

```json
{
  "title": "Approval of app texts", "lang": "en", "product": "Example app", "slug": "example-texts",
  "ui": {"…": "every interface string the page shows, in `lang`: each key page_template.html reads with t() and tMap()"},
  "round": 1, "final": false,
  "origin": {"branch": "main", "commit": "3f2a9c1"},
  "brief": "# Localization brief\n…",
  "files": {
    "source": {"lang": "uk", "path": "l10n/uk.json",
               "values": {"card.title": "Банківська картка", "items": {"one": "{n} товар", "few": "{n} товари", "many": "{n} товарів", "other": "{n} товару"}},
               "base": {"…": "project values at the last reconcile"}},
    "target": {"lang": "en", "path": "l10n/en.json", "values": {"…": "…"}, "base": {"…": "…"}}
  },
  "terms": [{"id": "банківська-картка", "source": "банківська картка", "target": "bank card",
             "meaning": "a payment card linked to the account", "variants": ["bank card", "card"],
             "match": {"stems": ["банківськ\\w* картк"], "keys": ["card.title"]}}],
  "questions": [{"id": "Q1", "title": "Formal or informal address?", "gist": "…",
                 "options": [{"key": "A", "text": "Formal", "consequence": "…"},
                             {"key": "B", "text": "Informal", "consequence": "…"}],
                 "recommendation": {"key": "A", "why": "…"}, "terms": [], "keys": []}],
  "review": [{"lang": "uk", "key": "card.title", "severity": "significant", "reason": "term",
              "was": "Банківська картка", "proposal": "Картка", "why": "…"}],
  "projectChanges": [], "invalid": [], "rejected": [],
  "codeDefects": [{"key": "pay.prefix", "text": "sentence split across two keys; join them in code"}],
  "risk": [{"keys": ["pay.confirm"], "class": "payment"}],
  "identical": [{"key": "brand.name", "why": "product name"}],
  "batches": [{"id": "pay", "label": "Payments", "prefixes": ["pay."], "expected": 2},
              {"id": "rest", "label": "Other", "prefixes": [], "expected": 4}]
}
```

- `values` — the artifact's texts; `base` — the project's values at the last reconcile; in
  round 1 `base` equals `values`.
- A plural is the object of CLDR forms as in the file — in `values`, `was` and `proposal` alike.
- `was` and `proposal` are the key's full strings. No full string derivable → `proposal` is
  empty and the instruction goes to `why`. A review row covering several keys is split per key.
- Term `id` — the source word in lower case, spaces as `-`, only letters of any alphabet, digits
  and `-`. A term without a translation has an empty `target`.
- A question's `title` quotes its Open questions item of the brief verbatim — `apply` finds the
  item by it. Options come only from the brief and the review — for a question raised by an
  editor's comment, also from that comment and the language pack; `recommendation` is omitted when
  none of them gives one.
- A question's `keys` — the locale keys it is about; `check` refuses an unknown key, and each
  named key's card lists the question.
- Batches: a key falls into the first batch whose prefix matches, in spec order; the last batch
  has no prefixes and takes the rest; `expected` is its key count.
- `projectChanges` (`{lang, key, kind, value}`), `invalid` (`{lang, key, reason}`) and `rejected`
  (`{lang, key, proposal}`) are written by `apply`; round 1 has them empty.
- A term's `approved` is the round whose answer set its `target`, written by `apply`; the page
  folds approved terms until someone opens or answers them.
- Round n+1 carries no `review` rows of the target language: its changes show as `changed`.
- Page ids are fixed by this shape and survive rounds: `key.<localeKey>`,
  `source.<localeKey>`, `comment.<localeKey>`, `review.<lang>.<localeKey>`, `term.<id>`, `q.<id>`.

Round 1 from ux-translate outputs:

| ux-translate output | spec field |
|---|---|
| brief | `brief`; Terms → `terms`; Open questions → `questions`; intentional-identity exceptions → `identical`; batch plan → `batches` |
| Review, source only, and "source defects found" | `review` rows with the source `lang` |
| Review of the target | `review` rows with the target `lang` |
| skips caused by the code | `codeDefects` |
| "needs a human" | `risk` |

### UI strings

Strings of the key card's fields, toggles and comment, the summary sections, the comment and review
filters and the export order panel; `{n}`, `{lang}` and `{text}` stay as written.

| key | uk | en |
|---|---|---|
| `reviewOverridden` | Перекрито правкою на вкладці «Ключі». | Overridden by an edit on the Keys tab. |
| `commentToggle` | Коментар | Comment |
| `divergeHint` | Відповідь іншого редактора відрізняється від вашої | Another editor's answer differs from yours |
| `divergeLine` | інша відповідь | different answer |
| `editedMark` | ваша правка | your edit |
| `conflictHint` | Текст змінено і тут, і в проєкті — оберіть, який залишити | The text changed both here and in the project — pick which one to keep |
| `restoreTo` | Повернути «{text}» | Restore “{text}” |
| `sectionSource` | Тексти джерела | Source texts |
| `sectionKeyComments` | Коментарі до ключів | Key comments |
| `filterCommented` | з коментарями | with comments |
| `filterReviewRows` | з пропозицією ревʼю | with a review proposal |
| `exportOrderTitle` | Порядок редакторів для {lang}.json | Editor order for {lang}.json |
| `exportOrderIntro` | Кілька редакторів змінили тексти. Кожен текст береться від першого в списку, хто його змінив. Закриття раунду це не зачіпає. | Several editors changed texts. Each text comes from the first editor in the list who changed it. Closing the round is not affected. |
| `exportOrderConfirm` | Вивантажити | Download |
| `commentsTitle` | Коментарі редакторів | Editors' comments |
| `roleSource` | основа | source |
| `roleTarget` | переклад | translation |

## Database

The page writes, you read:

- `log/<auto>` — `{object, by, at, round, pick, text, reviewed}`, one document per answer change;
  `object` is a page id, or `note.<id>` for an editor's comment (`pick: "custom"`, the comment in
  `text`; an empty pick and text withdraw it).
  - `key.<localeKey>` sets the target text (the source text when only the source has a project
    conflict), `source.<localeKey>` the source text (`pick: "custom"`, the text in `text`; an
    empty pick and text restore the round's text). Each shares a slot with
    `review.<lang>.<localeKey>` of the language it sets; `apply` takes the editor's latest
    value-setting answer in the slot.
  - `comment.<localeKey>` is a comment on one key, shaped like `note.<id>`; each author has their
    own.
- `editors/<userId>` — `{email, name, firstSeenAt}`.
- `rounds/<n>` — `{closedAt, by, priority: [userId, …]}`, written by the owner; its presence
  closes round n.

## Create

1. **Snapshot** — read both locale files in full into `files.*.values`; `origin` is the
   project's branch and `HEAD` commit. Locale files with uncommitted changes → ask the user first.
2. **Spec** — write `<scratch>/spec.json` by the shape and table above, `round: 1`.
3. **Check** — `python3 approval.py check <scratch>/spec.json` must print `ok`; fix each
   `spec:` line and rerun. Exit 0 ok, 1 spec errors, 2 usage error.
4. **Build** — `python3 approval.py build <scratch>/spec.json --stats` writes `page.html` beside
   the spec.
5. **Publish** — Artifact publish of `page.html` with an `icon`, `title` from the spec and:
   ```
   capabilities: {
     db: {rules: [
       {path: "log", read: "view", write: "admin"},
       {path: "editors", read: "view", write: "owner"},
       {path: "editors/{self}", write: "admin"},
       {path: "rounds", read: "view", write: "owner"}]},
     user: {scopes: ["profile"]},
     downloads: true}
   ```
6. **Verify** — `ArtifactData list` of `log`, `editors` and `rounds`, then each again with
   `as_level: "view"`. `set` of `rounds/probe` with `as_level: "admin"` must be refused; a write
   that lands means the rules are wrong — delete the probe, fix the declaration, republish.

## Next round

1. **Read** — Artifact read of the url; the saved `page.html` is `--previous` and the rollback.
   Its latest round is n.
2. **Answers** — `ArtifactData list` of `log` and `editors` (page with `query.limit` and
   `next_cursor`, or `out_dir`), `get` of `rounds/<n>`. An `editors` document with an empty
   `name` gets the display name `ArtifactData profiles` returns for its id. Save `log` and
   `editors` as one JSON file each in `<scratch>` — the list of `{id, data}` documents as
   returned — and the `rounds/<n>` document `{id, data}` as `round.json`.
3. **Apply** — `python3 approval.py apply <page.html> <log.json> <editors.json> <round.json>
   --project <root> -o <dir>`, `<dir>` a fresh folder in `<scratch>` (inside `<root>` → exit 2).
   It writes `spec-next.json`, `brief.md`, `<source>.json`, `<target>.json`, `named-keys.txt`,
   `changed-<target>.jsonl`, `conflicts.md`, `free-text.md`.
4. **Check editors' texts** — `python3 ../ux-translate/check_drafts.py <dir>/changed-<target>.jsonl
   --lang <target>` with `--ratio` as ux-translate runs it. Each key in a non-`warning:` line keeps
   its round-n value in `spec-next.json` and goes to `invalid` with the reported problem.
5. **Brief** — fold each answer of `free-text.md` into `<dir>/brief.md` where it belongs (a term,
   a decision, a rule). Each `note.*` line is an editor's comment: a settled fact goes into the
   brief; an open point becomes a question for the next round — options, consequences and a
   recommendation. Each `comment.<localeKey>` line is the same, and its question carries
   `keys: [<localeKey>]`.
6. **ux-translate** on the files in `<dir>` with `<dir>/brief.md`, only for the keys of
   `named-keys.txt` — naming them lifts its no-overwrite rule:
   - Review, source only → `review` rows of the source language;
   - Review and Translate of the target → texts written to `<dir>/<target>.json` after its exit 0.
     A named key in `changed-<target>.jsonl` has a target an editor set this round: it gets
     Review, not Translate.
   Its tables go to the artifact, not to the user: the next round is where editors answer them.
7. **Merge** — into `spec-next.json`: `brief` from `<dir>/brief.md`, the new source `review`
   rows, the questions raised by comments, the named keys' target texts into
   `files.target.values`. `apply` copies `ui` from the previous page: add each key of
   [UI strings](#ui-strings) that `ui` lacks, in the spec's `lang`.
8. **Check and build** — `python3 approval.py check <dir>/spec-next.json --previous <page.html>`
   must print `ok`; then `python3 approval.py build <dir>/spec-next.json --previous <page.html>
   --stats`.
9. **Publish** the new `<dir>/page.html` to the same url, without `capabilities`. Rollback:
   publish the saved previous `page.html` to that url.

## Finalize

1. Steps 1–4 of Next round; no ux-translate.
2. `spec-next.json` has a `conflict` in `projectChanges` or any `invalid`, or `named-keys.txt`
   is not empty → run Next round instead and tell the user why.
3. Otherwise set `final: true`, then steps 8–9 of Next round. The final round's export on the
   page is the approved set; applying it to the project is the user's own task.

## Report

In the user's language, one line each, empty ones omitted:

- artifact url and round number;
- branch and commit of the reconcile (`origin`);
- answers applied; disputes and their winners (`conflicts.md`);
- `invalid` keys with the reason; `project`, `conflict`, `added` and removed keys, counted;
- keys passed to ux-translate, counted;
- what Verify exercised and what it could not (Create);
- the next action: editors answer, the owner closes the round.
