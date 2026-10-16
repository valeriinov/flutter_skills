---
name: ux-approval
description: Run UI text approval rounds in a shared artifact: create, next round from answers and the project, finalize. Use for "утверди тексты", "следующий раунд", "approval round".
argument-hint: "[ ux-translate brief, review and locale files | artifact url + next round | artifact url + finalize ]"
---

Run from the project whose branch will receive the approved texts. The artifact is the source of
truth until the export: each round keeps its brief, a snapshot of every key, the review and the
answers. You publish the artifact and read its database yourself. The project is only read —
for the reconcile and for key context; its files are never written, except the `Approval:` line of
its `approval-queue.md` ([Approval queue](#approval-queue)). Working files go to the
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
    "targets": [{"lang": "en", "path": "l10n/en.json", "values": {"…": "…"}, "base": {"…": "…"}},
                {"lang": "fr", "path": "l10n/fr.json", "values": {"…": "…"}, "base": {"…": "…"}}]
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
  "projectChanges": [], "invalid": [], "interpreted": [], "rejected": [],
  "codeDefects": [{"key": "pay.confirm", "text": "One button for two different dialogs: no text fits both",
                   "uses": [{"where": "Leaving the cart", "question": "Leave without paying?", "action": "leaves the cart", "needed": "Leave"},
                            {"where": "Removing a card", "question": "Remove this card?", "action": "removes the card", "needed": "Remove"}],
                   "why": "…", "now": "…", "devTask": "Split into two keys: …"}],
  "compositions": [{"id": "pay-total", "keys": ["pay.prefix", "pay.items"], "pattern": "{pay.prefix} {n} {pay.items#n}",
                    "sample": {"n": 3}, "site": "lib/pay/total.dart:42"}],
  "risk": [{"keys": ["pay.confirm"], "class": "payment",
            "why": "The text confirms a charge: a wrong word makes people pay by mistake or abandon payment."}],
  "identical": [{"key": "brand.name", "why": "product name"}],
  "batches": [{"id": "pay", "label": "Payments", "prefixes": ["pay."], "expected": 2},
              {"id": "rest", "label": "Other", "prefixes": [], "expected": 4}]
}
```

- `values` — the artifact's texts; `base` — the project's values at the last reconcile; in
  round 1 `base` equals `values`.
- `files.targets` — one entry per translation, the first one fixed across rounds; a spec with
  `files.target` (one object) reads as a list of one, `apply` writes `targets`. `check` refuses a
  repeated language and a source key starting with `<lang>.` of a later target. Terms, questions
  and the decision rows of the brief belong to the first target.
- A plural is the object of CLDR forms as in the file — in `values`, `was` and `proposal` alike.
- `was` and `proposal` are the key's full strings. No full string derivable → `proposal` is
  empty and the instruction goes to `why`. A review row covering several keys is split per key.
- Every key below high confidence shows "Що вирішити" on its card: one line per reason (review
  row, code defect, risk, invalid or interpreted edit, question, project change, change since the
  last round, untranslated term), with "Детальніше" opening the review row with its answer buttons
  (the same answer as on the Review tab), the defect fields and the risk class's `why`.
- `risk` items may carry `why`: what goes wrong for the user if a text of that class is wrong.
- `codeDefects` — a defect only the code can fix. Its readers are analysts and designers, not
  developers: say what the user sees, never file names or identifiers. `text` is one line: what is
  wrong and what it means for the text. `uses` lists each place the key shows (`where` as the user
  names the screen or dialog, `question` the text around it, `action` what the control does,
  `needed` the text that place calls for); `why` is the problem in two sentences, `now` what an
  editor does this round, `devTask` the change in code, worded for a ticket. All but `key` and
  `text` are optional; the card shows `text` and folds the rest under "Детальніше". A key in a
  composition shows its phrase under `text` too.
- `compositions` — a phrase the code assembles from several keys. `pattern` is the assembly as the
  code does it: `{<localeKey>}` for a key, `{<name>}` for a `sample` value, `{<localeKey>#<name>}`
  for a plural key counted by that sample value. Each named key's card shows the assembled phrase
  in both languages with its own part marked; `check` refuses a key outside the source values, a
  key of `keys` the pattern lacks, a token naming neither, and a non-numeric count. A
  placeholder inside a key's text takes the sample value of its name; a positional `{}` takes
  `sample[""]`.
- `interpreted` (`{lang, key, text, by}`) — an editor's text that failed the checks and that you
  rewrote by its evident intent: `text` and `by` are the editor's original and name, the key's
  value is your rewrite. The key drops to low confidence and its card quotes the original.
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
  (`{lang, key, proposal}`) are written by `apply`; round 1 has them empty, as `interpreted`,
  except the `added` entries of the queued keys ([Approval queue](#approval-queue)).
- Confidence is computed per language too: the key-wide reasons (question, risk, code defect) count
  for every language, the rest for the language they name, an untranslated term for the target.
  The card shows each language's level beside its text and the worst one in the head. An
  untranslated term counts for every target.
- `text_rules.json` holds the rules both `apply` and the page run on an editor's text: a script
  foreign to the language, placeholders differing from the round's text, an empty plural form.
- A term's `approved` is the round whose answer set its `target`, written by `apply`; the page
  folds approved terms until someone opens or answers them. `apply` also writes each approved term
  into the Terms table of the brief: the row whose first cell is the term's `source` (any case) gets
  `target` in its second cell and `accepted` in the `status` column, if the table has one; without
  such a row a new one gets `source`, `target`, `meaning` in the column whose header starts with
  `meaning`, `accepted` in `status`, the rest empty. The brief thus carries every approved term.
- A row nobody answered, whose `was` still matches the text, `apply` carries into round n+1 as
  is, in any language. A target text an editor set in round n gets a row of its own from `apply`:
  `minor`, empty `proposal`, `why` from `editedReviewWhy` (English when `ui` lacks it); the
  Review of step 6 replaces it.
- Page ids are fixed by this shape and survive rounds: `key.<localeKey>` for the first target,
  `key.<lang>.<localeKey>` for every later one, `source.<localeKey>`, `comment.<localeKey>`,
  `review.<lang>.<localeKey>`, `term.<id>`, `q.<id>`.
- The Review and Keys tabs show the source with one target at a time; with two or more targets a
  switcher above the list picks the pair and counts each pair's answers.

Round 1 from ux-translate outputs:

| ux-translate output | spec field |
|---|---|
| brief | `brief`; Terms rows with status `proposal` and terms without a translation → `terms` (`accepted` rows stay only in the brief); Open questions → `questions`; intentional-identity exceptions → `identical`; batch plan → `batches` |
| Review, source only, and "source defects found" | `review` rows with the source `lang` |
| Review of a target | `review` rows with that target's `lang` |
| skips caused by the code | `codeDefects` with `uses`, `why`, `now`, `devTask` read from the code at each call site; for each one assembled from several keys, also `compositions` — grep the code for the key and copy its assembly |
| "needs a human" | `risk`, each class with `why`: what goes wrong for the user if its text is wrong, in words for analysts and designers |

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
| `exportTerms` | Словник (md) | Glossary (md) |
| `commentsTitle` | Коментарі редакторів | Editors' comments |
| `roleSource` | основа | source |
| `roleTarget` | переклад | translation |
| `confidenceOverall` | Найнижча впевненість серед мов ключа | The lowest confidence among the key's languages |
| `langWhy` | Чому: {reasons} ↑ | Why: {reasons} ↑ |
| `phraseTitle` | Частина фрази {pattern}; виділено цей ключ | Part of the phrase {pattern}; this key is marked |
| `phraseSite` | Збирається в коді: {site} | Assembled in code: {site} |
| `interpretedNote` | {lang}: правку {who} «{text}» витлумачено як поточний текст; не так — виправте | {lang}: {who}'s edit “{text}” was read as the current text; fix it if that is wrong |
| `issuesNote` | Ця правка не застосується: {issues}. Пояснення — у «Коментар» | This edit will not apply: {issues}. Put explanations in Comment |
| `issue_foreignScript` | літери іншої абетки | letters of another alphabet |
| `issue_placeholders` | змінні мають бути {detail} | placeholders must be {detail} |
| `issue_emptyForm` | порожня форма {detail} | empty form {detail} |
| `pairsLabel` | Пара мов | Language pair |
| `defectMore` | Детальніше | Details |
| `defectLess` | Згорнути | Hide |
| `defectComposed` | Фраза складається з кількох ключів: перевіряйте її цілком | The phrase is assembled from several keys: check it whole |
| `defectUses` | Де використовується | Where it shows |
| `defectWhy` | Чому це проблема | Why it is a problem |
| `defectNow` | Що зробити зараз | What to do now |
| `defectDevTask` | Що потрібно від розробки | What development needs to do |
| `defectTaskTag` | задача | task |
| `useQuestion` | Текст: «{text}» | Text: “{text}” |
| `useAction` | Кнопка {text} | The button {text} |
| `useNeeded` | Тут потрібно: | Needed here: |
| `reasonComposed` | склейка фрази | assembled phrase |
| `decideTitle` | Що вирішити | What to decide |
| `decideReview` | {lang}: ревʼю пропонує інший текст ({severity}) | {lang}: the review proposes another text ({severity}) |
| `decideDefect` | Дефект коду | Code defect |
| `decideRisk` | Ризик: {risk} | Risk: {risk} |
| `decideQuestion` | Питання {id}: {title} | Question {id}: {title} |
| `decideChanged` | {lang}: текст змінено з раунду {n} | {lang}: text changed since round {n} |
| `decideTerm` | Термін без перекладу: «{term}» | Untranslated term: “{term}” |
| `reviewNow` | Зараз | Now |
| `reviewProposes` | Ревʼю пропонує | The review proposes |
| `reviewWhy` | Чому | Why |
| `decideSameAnswer` | Та сама відповідь, що на вкладці «Ревʼю»: зміниться і там. | The same answer as on the Review tab: it changes there too. |
| `editedReviewWhy` | Текст змінено в раунді {n} ({who}); перевірте | {who} changed this text in round {n}; check it |

`reasonCode` is a map, one entry per reason kind: `question` питання / question, `risk` ризик /
risk, `codeDefect` дефект коду / code defect, `review` ревʼю / review, `conflict` конфлікт з
проєктом / conflict with the project, `invalid` правка не пройшла перевірку / edit failed the check,
`interpreted` правку витлумачено / edit interpreted, `changed` змінено з минулого раунду / changed
since the last round, `term` термін без перекладу / untranslated term, `project` змінено в проєкті /
changed in the project, `added` новий ключ / new key.

## Database

The page writes, you read:

- `log/<auto>` — `{object, by, at, round, pick, text, reviewed}`, one document per answer change;
  `object` is a page id, or `note.<id>` for an editor's comment (`pick: "custom"`, the comment in
  `text`; an empty pick and text withdraw it).
  - `key.<localeKey>` sets the first target's text (the source text when only the source has a
    project conflict), `key.<lang>.<localeKey>` that target's text, `source.<localeKey>` the
    source text (`pick: "custom"`, the text in `text`; an empty pick and text restore the round's
    text). Each shares a slot with `review.<lang>.<localeKey>` of the language it sets; `apply`
    takes the editor's latest value-setting answer in the slot.
  - `comment.<localeKey>` is a comment on one key, shaped like `note.<id>`; each author has their
    own.
- `editors/<userId>` — `{email, name, firstSeenAt}`.
- `rounds/<n>` — `{closedAt, by, priority: [userId, …]}`, written by the owner; its presence
  closes round n.

## Approval queue

`approval-queue.md` lies beside the project's brief, whose path the `## Localization` section of
the project's AGENTS.md names; it holds the line `Approval: <artifact url>, round <n>, <open | final
| applied>` and the table `| key | date |` of keys awaiting approval. No such section → the queue
is not read, no `Approval:` line is written, and the Report says so.

- Create puts each queued key into `projectChanges` as `{lang, key, kind: added, value}`, one entry
  per language whose file has the key, so editors see it.
- Next round reads no queue: the reconcile already marks keys changed in the project `added` or
  `project` and names them in `named-keys.txt`.
- After each publish write one line `Approval: <url>, round <n>, open` (Finalize: `final`) into
  the queue file in the working tree, replacing its previous `Approval:` line; no file → create it
  with that line and the empty `| key | date |` table. Do not commit it.

## Create

1. **Snapshot** — read every locale file in full into `files.source.values` and
   `files.targets[].values`; `origin` is the project's branch and `HEAD` commit. Locale files with uncommitted changes → ask the user first.
   Read the queue ([Approval queue](#approval-queue)).
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
   Then write the `Approval:` line ([Approval queue](#approval-queue)).
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
   It writes `spec-next.json`, `brief.md`, `<lang>.json` per language, `named-keys.txt`,
   `changed-<target>.jsonl` per target, `conflicts.md`, `free-text.md`, `suspect.jsonl`.
4. **Check editors' texts** — for each target, `python3 ../ux-translate/check_drafts.py
   <dir>/changed-<target>.jsonl --lang <target>` with `--ratio` as ux-translate runs it. Each key
   in a non-`warning:` line keeps its round-n value in `spec-next.json` and goes to `invalid` with
   the reported problem. A key whose value this step sets loses its `review` row of that language.
   Each line of `suspect.jsonl` is an editor's text that failed `text_rules.json` — often a comment
   typed into the text field. Its intent evident (one reading only) → write the text it asks for in
   that language into `spec-next.json` and `<dir>/<lang>.json`, and add `{lang, key, text, by}` from
   the line to `interpreted`. Ambiguous → the key keeps its round-n value, goes to `invalid`, and the
   text becomes a question as in step 5, `keys: [<key>]`.
5. **Brief** — `apply` has already put the `term.*` answers into `<dir>/brief.md`; fold each
   `note.*`, `comment.*` and `q.*` answer of `free-text.md` into it where it belongs (a decision, a
   rule). Each `note.*` line is an editor's comment: a settled fact goes into the
   brief; an open point becomes a question for the next round — options, consequences and a
   recommendation. Each `comment.<localeKey>` line is the same, and its question carries
   `keys: [<localeKey>]`.
6. **ux-translate** on the files in `<dir>` with `<dir>/brief.md`, only for the keys of
   `named-keys.txt` — naming them lifts its no-overwrite rule:
   - Review, source only → `review` rows of the source language;
   - Review and Translate of each target → texts written to `<dir>/<target>.json` after its exit 0;
   - Review of each target, also for every key of `changed-<target>.jsonl` → `review` rows of that
     target. Such a key has a text an editor set this round: it gets Review, not Translate. A key
     whose Review finds nothing keeps the row `apply` wrote.
   Its tables go to the artifact, not to the user: the next round is where editors answer them.
7. **Merge** — into `spec-next.json`: `brief` from `<dir>/brief.md`, the new source and target
   `review` rows (a new row replaces a carried row of the same language and key), the questions
   raised by comments, the named keys' target texts into `files.targets[].values`, `interpreted`
   from step 4, and
   `compositions` for codeDefects keys that lack one (as in the Create table). `apply` copies `ui`
   from the previous page: add each key of [UI strings](#ui-strings) that `ui` lacks, in the spec's
   `lang`, and rewrite the `why` of the rows `apply` wrote for editors' texts by `editedReviewWhy`.
8. **Check and build** — `python3 approval.py check <dir>/spec-next.json --previous <page.html>`
   must print `ok`; then `python3 approval.py build <dir>/spec-next.json --previous <page.html>
   --stats`.
9. **Publish** the new `<dir>/page.html` to the same url with `title` from the spec, without
   `capabilities`. Rollback: publish the saved previous `page.html` to that url. Then write the
   `Approval:` line ([Approval queue](#approval-queue)).
10. **Duplicates** — search `--project` for a second source of truth on terms: a markdown file
    outside `plan/`, other than the brief and `approval-queue.md`, with a table where at least two
    rows match terms of `<dir>/brief.md` (any case; `meaning` by sense, not wording) by the first
    Terms column, by the source-variants-to-flag column or by `meaning`, or with a heading only the
    brief has (`Terms`, `Do not use`, `Text component catalogue`). A table whose value column holds
    code identifiers in backticks is a code glossary and not a duplicate. The project is not written: duplicates go to the
    Report.

## Finalize

1. Steps 1–4 of Next round; no ux-translate.
2. `spec-next.json` has a `conflict` in `projectChanges` or any `invalid`, or `named-keys.txt`
   is not empty → run Next round instead and tell the user why.
3. Otherwise set `final: true`, then steps 8–10 of Next round. The final round's export on the
   page is the approved set; apply it from the project with ux-translate, mode Apply approved,
   passing the export and the reconcile commit.

## Report

In the user's language, one line each, empty ones omitted:

- artifact url and round number;
- branch and commit of the reconcile (`origin`);
- answers applied; disputes and their winners (`conflicts.md`);
- `invalid` keys with the reason; `interpreted` keys with the editor's original; `project`, `conflict`, `added` and removed keys, counted;
- keys passed to ux-translate, counted;
- what Verify exercised and what it could not (Create);
- the `Approval:` line written to `approval-queue.md` and left uncommitted, or that the project's
  AGENTS.md has no `## Localization` section, so the queue was not read;
- duplicates of the brief, `path | what it repeats`: remove them with ux-translate Brief, or Apply
  approved after Finalize;
- the next action: editors answer, the owner closes the round; after Finalize — ux-translate,
  mode Apply approved, with the export and the reconcile commit.
